// Copyright 2017 Parity Technologies (UK) Ltd.
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the "Software"),
// to deal in the Software without restriction, including without limitation
// the rights to use, copy, modify, merge, publish, distribute, sublicense,
// and/or sell copies of the Software, and to permit persons to whom the
// Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
// OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
// FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
// DEALINGS IN THE SOFTWARE.

//! Protocol negotiation strategies for the peer acting as the listener
//! in a multistream-select protocol negotiation.

use crate::protocol::{HeaderLine, Message, MessageIO, Protocol, ProtocolError};
use crate::{Negotiated, NegotiationError};

use futures::prelude::*;
use smallvec::SmallVec;
use std::{
    convert::TryFrom as _,
    iter::FromIterator,
    mem,
    pin::Pin,
    task::{Context, Poll},
};

/// Returns a `Future` that negotiates a protocol on the given I/O stream
/// for a peer acting as the _listener_ (or _responder_).
///
/// This function is given an I/O stream and a list of protocols and returns a
/// computation that performs the protocol negotiation with the remote. The
/// returned `Future` resolves with the name of the negotiated protocol and
/// a [`Negotiated`] I/O stream.
pub fn listener_select_proto<R, I>(inner: R, protocols: I) -> ListenerSelectFuture<R, I::Item>
where
    R: AsyncRead + AsyncWrite,
    I: IntoIterator,
    I::Item: AsRef<[u8]>,
{
    let protocols = protocols
        .into_iter()
        .filter_map(|n| match Protocol::try_from(n.as_ref()) {
            Ok(p) => Some((n, p)),
            Err(e) => {
                log::warn!(
                    "Listener: Ignoring invalid protocol: {} due to {}",
                    String::from_utf8_lossy(n.as_ref()),
                    e
                );
                None
            }
        });
    ListenerSelectFuture {
        protocols: SmallVec::from_iter(protocols),
        state: State::RecvHeader {
            io: MessageIO::new(inner),
        },
        last_sent_na: false,
    }
}

/// The `Future` returned by [`listener_select_proto`] that performs a
/// multistream-select protocol negotiation on an underlying I/O stream.
#[pin_project::pin_project]
pub struct ListenerSelectFuture<R, N> {
    // TODO: It would be nice if eventually N = Protocol, which has a
    // few more implications on the API.
    protocols: SmallVec<[(N, Protocol); 8]>,
    state: State<R, N>,
    /// Whether the last message sent was a protocol rejection (i.e. `na\n`).
    ///
    /// If the listener reads garbage or EOF after such a rejection,
    /// the dialer is likely using `V1Lazy` and negotiation must be
    /// considered failed, but not with a protocol violation or I/O
    /// error.
    last_sent_na: bool,
}

enum State<R, N> {
    // 从Dialer收到了Header信息。
    // 首先检查Header是否合法，若合法，跳转到SendHeader状态。
    RecvHeader {
        io: MessageIO<R>,
    },
    // 调用start_send函数，准备发送自己的Header信息，
    // 并跳转到Flush状态。注意此时协议协商未完成，因此使用的协议暂定为None。
    SendHeader {
        io: MessageIO<R>,
    },
    // 首先进行合法性判断，若不合法则报告错误原因，协商狮白。
    // 否则，根据收到消息的不同（ls请求或一个具体建议）执行不同操作，
    // 并跳转到SendMessage状态。
    // - ls：返回自己支持的所有协议
    // - 具体建议：若己方支持建议的协议，则复读以示肯定；否则返回NA。
    RecvMessage {
        io: MessageIO<R>,
    },
    // 根据发送的消息来设置自身的last_sent_na字段。
    // 然后，调用start_send函数并跳转至Flush状态。
    SendMessage {
        io: MessageIO<R>,
        message: Message,
        protocol: Option<N>,
    },
    // 发送消息。若已确定使用的协议，则使用该协议发送确认信息；
    // 否则跳转到RecvMessage状态。
    Flush {
        io: MessageIO<R>,
        protocol: Option<N>,
    },
    Done,
}

impl<R, N> Future for ListenerSelectFuture<R, N>
where
    // The Unpin bound here is required because we produce a `Negotiated<R>` as the output.
    // It also makes the implementation considerably easier to write.
    R: AsyncRead + AsyncWrite + Unpin,
    N: AsRef<[u8]> + Clone,
{
    type Output = Result<(N, Negotiated<R>), NegotiationError>;

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        let this = self.project();

        loop {
            match mem::replace(this.state, State::Done) {
                State::RecvHeader { mut io } => {
                    match io.poll_next_unpin(cx) {
                        Poll::Ready(Some(Ok(Message::Header(h)))) => match h {
                            HeaderLine::V1 => *this.state = State::SendHeader { io },
                        },
                        Poll::Ready(Some(Ok(_))) => {
                            return Poll::Ready(Err(ProtocolError::InvalidMessage.into()))
                        }
                        Poll::Ready(Some(Err(err))) => return Poll::Ready(Err(From::from(err))),
                        // Treat EOF error as [`NegotiationError::Failed`], not as
                        // [`NegotiationError::ProtocolError`], allowing dropping or closing an I/O
                        // stream as a permissible way to "gracefully" fail a negotiation.
                        Poll::Ready(None) => return Poll::Ready(Err(NegotiationError::Failed)),
                        Poll::Pending => {
                            *this.state = State::RecvHeader { io };
                            return Poll::Pending;
                        }
                    }
                }

                State::SendHeader { mut io } => {
                    match Pin::new(&mut io).poll_ready(cx) {
                        Poll::Pending => {
                            *this.state = State::SendHeader { io };
                            return Poll::Pending;
                        }
                        Poll::Ready(Ok(())) => {}
                        Poll::Ready(Err(err)) => return Poll::Ready(Err(From::from(err))),
                    }

                    let msg = Message::Header(HeaderLine::V1);
                    if let Err(err) = Pin::new(&mut io).start_send(msg) {
                        return Poll::Ready(Err(From::from(err)));
                    }

                    *this.state = State::Flush { io, protocol: None };
                }

                State::RecvMessage { mut io } => {
                    let msg = match Pin::new(&mut io).poll_next(cx) {
                        Poll::Ready(Some(Ok(msg))) => msg,
                        // Treat EOF error as [`NegotiationError::Failed`], not as
                        // [`NegotiationError::ProtocolError`], allowing dropping or closing an I/O
                        // stream as a permissible way to "gracefully" fail a negotiation.
                        //
                        // This is e.g. important when a listener rejects a protocol with
                        // [`Message::NotAvailable`] and the dialer does not have alternative
                        // protocols to propose. Then the dialer will stop the negotiation and drop
                        // the corresponding stream. As a listener this EOF should be interpreted as
                        // a failed negotiation.
                        Poll::Ready(None) => return Poll::Ready(Err(NegotiationError::Failed)),
                        Poll::Pending => {
                            *this.state = State::RecvMessage { io };
                            return Poll::Pending;
                        }
                        Poll::Ready(Some(Err(err))) => {
                            if *this.last_sent_na {
                                // When we read garbage or EOF after having already rejected a
                                // protocol, the dialer is most likely using `V1Lazy` and has
                                // optimistically settled on this protocol, so this is really a
                                // failed negotiation, not a protocol violation. In this case
                                // the dialer also raises `NegotiationError::Failed` when finally
                                // reading the `N/A` response.
                                if let ProtocolError::InvalidMessage = &err {
                                    log::trace!(
                                        "Listener: Negotiation failed with invalid \
                                        message after protocol rejection."
                                    );
                                    return Poll::Ready(Err(NegotiationError::Failed));
                                }
                                if let ProtocolError::IoError(e) = &err {
                                    if e.kind() == std::io::ErrorKind::UnexpectedEof {
                                        log::trace!(
                                            "Listener: Negotiation failed with EOF \
                                            after protocol rejection."
                                        );
                                        return Poll::Ready(Err(NegotiationError::Failed));
                                    }
                                }
                            }

                            return Poll::Ready(Err(From::from(err)));
                        }
                    };

                    match msg {
                        Message::ListProtocols => {
                            let supported =
                                this.protocols.iter().map(|(_, p)| p).cloned().collect();
                            let message = Message::Protocols(supported);
                            *this.state = State::SendMessage {
                                io,
                                message,
                                protocol: None,
                            }
                        }
                        Message::Protocol(p) => {
                            let protocol = this.protocols.iter().find_map(|(name, proto)| {
                                if &p == proto {
                                    Some(name.clone())
                                } else {
                                    None
                                }
                            });

                            let message = if protocol.is_some() {
                                log::debug!("Listener: confirming protocol: {}", p);
                                Message::Protocol(p.clone())
                            } else {
                                log::debug!(
                                    "Listener: rejecting protocol: {}",
                                    String::from_utf8_lossy(p.as_ref())
                                );
                                Message::NotAvailable
                            };

                            *this.state = State::SendMessage {
                                io,
                                message,
                                protocol,
                            };
                        }
                        _ => return Poll::Ready(Err(ProtocolError::InvalidMessage.into())),
                    }
                }

                State::SendMessage {
                    mut io,
                    message,
                    protocol,
                } => {
                    match Pin::new(&mut io).poll_ready(cx) {
                        Poll::Pending => {
                            *this.state = State::SendMessage {
                                io,
                                message,
                                protocol,
                            };
                            return Poll::Pending;
                        }
                        Poll::Ready(Ok(())) => {}
                        Poll::Ready(Err(err)) => return Poll::Ready(Err(From::from(err))),
                    }

                    if let Message::NotAvailable = &message {
                        *this.last_sent_na = true;
                    } else {
                        *this.last_sent_na = false;
                    }

                    if let Err(err) = Pin::new(&mut io).start_send(message) {
                        return Poll::Ready(Err(From::from(err)));
                    }

                    *this.state = State::Flush { io, protocol };
                }

                State::Flush { mut io, protocol } => {
                    match Pin::new(&mut io).poll_flush(cx) {
                        Poll::Pending => {
                            *this.state = State::Flush { io, protocol };
                            return Poll::Pending;
                        }
                        Poll::Ready(Ok(())) => {
                            // If a protocol has been selected, finish negotiation.
                            // Otherwise expect to receive another message.
                            match protocol {
                                Some(protocol) => {
                                    log::debug!(
                                        "Listener: sent confirmed protocol: {}",
                                        String::from_utf8_lossy(protocol.as_ref())
                                    );
                                    let io = Negotiated::completed(io.into_inner());
                                    return Poll::Ready(Ok((protocol, io)));
                                }
                                None => *this.state = State::RecvMessage { io },
                            }
                        }
                        Poll::Ready(Err(err)) => return Poll::Ready(Err(From::from(err))),
                    }
                }

                State::Done => panic!("State::poll called after completion"),
            }
        }
    }
}
