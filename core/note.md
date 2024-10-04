# libp2p-core代码结构速览

在`cargo metadata`中的标记为`path+file://.../rust-libp2p-pg/core#libp2p-core@0.39.1`。从名字和文档中不难推断出，`core`库是libp2p的核心模块，而从`Cargo.toml`中的记载来看，本库定义了rust-libp2p的核心trait和结构体。

根据仓库readme的说法，几乎所有rust-libp2p的实现都依赖于本库。观察本库的依赖项，会发现它有`libp2p-identity`、`multistream-select`和`rw-stream-sink`三个指向代码仓库中的相对路径的依赖项。这说明`core`库并非整个代码仓库的依赖树的根，它在依赖树上还有父节点。有关这三个库的代码结构速览，请见<a href="../identity/note.md" target="_self">libp2p-identity代码结构速览</a>、<a href="../misc/multistream-select/note.md" target="_self">multistream-select代码结构速览</a>和<a href="../misc/rw-stream-sink/note.md" target="_self">rw-stream-sink代码结构速览</a>三节。

`src/lib.rs`并未提供太多有效信息，只是声明了非常多模块，分别为`connection, either, muxing, peer_record, signed_envelope, transport, upgrade`。接下来我们一个一个地阅读它们。

```no_run
github.com/AlDanial/cloc v 1.90  T=0.02 s (1903.7 files/s, 341664.2 lines/s)
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
Rust                            32            630           1290           4247
Markdown                         2            178              0            358
TOML                             1              5              2             48
Protocol Buffers                 2             11             26             18
Bourne Shell                     1              0              2              5
-------------------------------------------------------------------------------
SUM:                            38            824           1320           4676
-------------------------------------------------------------------------------
```

## connection

很短，165行。

定义`Endpoint`枚举，其中只包含`Dialer`和`Listener`两种类型。

定义`ConnectedPoint`枚举：

```rust
pub enum ConnectedPoint {
    /// We dialed the node.
    Dialer {
        /// 通信对方的地址。
        address: Multiaddr,
        /// 有时本地节点需要兼职其他职责，例如Dialer有时需要兼职做Listener。
        /// 该选项对NAT和防火墙穿透有用。举例而言，在TCP协议中双方都是Dialer，
        /// 那么在upgrade到其他需要一Dialer一Listener的协议时，就需要用role_override选项，通过一些协商流程（DCUtR等），让其中某个Dialer退化为Listener。
        role_override: Endpoint,
    },
    /// We received the node.
    Listener {
        /// 自身的地址。
        local_addr: Multiaddr,
        /// 通信对方的地址。
        send_back_addr: Multiaddr,
    },
}
```

通过实现各种`From` trait，可以将`ConnectedPoint`转换为`Endpoint`。

此外，`ConnectedPoint`上还定义了一个奇怪的`is_relayed`方法，该方法用于判断是否为中继节点。其判断依据似乎是：自身的multiaddr是否包含P2pCircuit协议。包含该协议是中继节点的充分必要条件。

## muxing

其核心在于`StreamMuxer` trait。该trait定义了四个异步的“回调”函数，其中：

- `poll_inbound`：在需要处理流量时使用。
- `poll_outbound`：在需要发送出站流量时使用。
- `poll_close`：在关闭连接时使用。
- `poll`：在其他情况下**无条件**地触发。

若某个`struct A`实现了`StreamMuxer`，那么它一定拥有一个连接（connection），并且有能力将这个连接细分为多个子数据流（substream）。一个连接中的子数据流互相独立，互不影响，且可以使用不同的协议。

值得注意的是，`StreamMuxer` trait定义了一个poll方法，这个方法返回一个`Result`，以`StreamMuxerEvent`作为成功结果。后者是一个枚举，定义了connection回传的事件。目前只有一种，即`AddressChange`，表示远端的地址发生了变化。

在此基础上，定义`StreamMuxerExt`（Stream Muxer Extension） trait，它扩展了`StreamMuxer` trait，增加了一些方法，为unpin的数据结构也实现了`StreamMuxer` trait的类似功能。值得注意的是，在实现`close`方法时，模块专门写了一个`Close<S>(S)`结构体，并在实现其`Future` trait时，调用了`self.0.poll_close_unpin()`方法。

## transport

比较长，568行。本模块的核心是`Transport` trait，其规定了两个方面的接口：

- 和其他节点**建立连接**。
- 和其他节点进行**协议协商**。

在一众接口中，有一个特别的`address_translation`接口，它的作用是应对NAT的：当节点不满足于只监听局域网内的节点，还想监听外边的节点，就需要一次地址转化。

这个模块用到了非常多自定义的结构体，包括但不限于`boxed::Boxed, map::Map, map_err::MapErr, OrTransport, and_then::AndThen, upgrade::Builder`等。感觉是个可以拆出去做单独模块化的点。

定义`TransportEvent`枚举。其中的枚举项的意义已经附在代码上。

## either

它**直接使用**（而非自行实现）了两种Either：`future::Either`和`either::Either`。这俩Either在作用上差不多，都能包含两种数据类型，类似于`Result<T, E>`。

接下来，它为这些数据类型实现了几个trait：

- 为`future::Either<A, B>`实现`StreamMuxer` trait。实现方法是，规定泛型`A, B`均已实现`StreamMuxer` trait，然后用它们各自的`poll_inbound`等方法来实现`future::Either<A, B>`的`poll_inbound`方法。
- 为`either::Either<A, B>`实现`Transport` trait。实现方法和上述类似，规定泛型`A, B`均已实现`Transport` trait，然后用它们各自的`dial`等方法来实现`either::Either<A, B>`的`dial`方法。

除此以外，该模块定义了新数据结构：

```rust
pub enum EitherFuture<A, B> {
    First(#[pin] A),
    Second(#[pin] B),
}
```

随后实现了`EitherFuture<AFuture, BFuture>`的`Future` trait，其中`AFuture`和`BFuture`均实现`TryFuture<Ok = XInner>`。实现方法是调用`AFuture`或`BFuture`的`try_poll`方法，返回

```rust
Result<
    future::Either<AInner, BInner>,
    Either<AFuture::Error, BFuture::Error>,
>
```

## signed_envelope

核心数据结构如下：

```rust
pub struct SignedEnvelope {
    key: PublicKey,
    payload_type: Vec<u8>,
    payload: Vec<u8>,
    signature: Vec<u8>,
}
```

## peer_record

核心数据结构如下：

```rust
pub struct PeerRecord {
    peer_id: PeerId,
    seq: u64,
    addresses: Vec<Multiaddr>,

    /// A signed envelope representing this [`PeerRecord`].
    ///
    /// If this [`PeerRecord`] was constructed from a [`SignedEnvelope`], this is the original instance.
    envelope: SignedEnvelope,
}
```

## upgrade

前文已经提及，libp2p中包含一种upgrade操作，其本质是令通信双方切换到某种协议上去。一次upgrade步骤如下：

- 协议协商，由`UpgradeInfo::protocol_info()`方法完成，会用到之前提过的`multistream-select`模块。
- 握手。一旦协商成功，即使用`InboundUpgrade::upgrade_inbound`或`OutboundUpgrade::upgrade_outbound`方法。这俩方法都会返回一个`Future`，用于处理后续的握手通信。

为此，设计三个专用trait：

- `UpgradeInfo`：描述了一种协议，包括其名称、版本、协议号、协议参数等。
    ```rust
    pub trait UpgradeInfo {
        /// 一条协议的类型
        type Info: AsRef<str> + Clone;
        /// 包含一大堆“一条协议”的迭代器类型
        type InfoIter: IntoIterator<Item = Self::Info>;

        /// 返回上述迭代器
        fn protocol_info(&self) -> Self::InfoIter;
    }
    ```
- `InboundUpgrade`：用于处理入站连接的upgrade。**继承**自`UpgradeInfo` trait，它进一步定义了协商成功时的输出类型、失败时的错误类型和最终返回的`Future`类型，并规定了一个`upgrade_inbound`方法。
    ```rust
    /// 在入站的connection 或 substream上尝试一次upgrade
    pub trait InboundUpgrade<C>: UpgradeInfo {
        /// upgrade成功协商，且握手全部完成时的输出类型
        type Output;
        /// 握手时可能出现的错误类型
        type Error;
        /// 执行握手的Future类型
        type Future: Future<Output = Result<Self::Output, Self::Error>>;

        /// 当确定接下来要upgrade的目标协议时，调用这个方法以开始握手
        /// `info`是一条协议的唯一标识，由`protocol_info`方法提供
        fn upgrade_inbound(self, socket: C, info: Self::Info) -> Self::Future;
    }
    ```
- `OutboundUpgrade`：用于处理出站连接的upgrade。大体和前者相同，但规定的方法是`upgrade_outbound`。

此外，还定义了Connection上做ungrade专用的`InboundConnectionUpgrade`和`OutboundConnectionUpgrade` trait。它们的作用和上述`InboundUpgrade`和`OutboundUpgrade`类似，但它们的泛型参数是`T`，而不是`C`。

该模块包含数个子模块，存储于`upgrade`目录中。其中的几个子模块值得注意：

- `error`：它规定了枚举`UpgradeError`，其中有两种升级错误：协商错误`Select(NegotiationError)`和协商后错误`Apply(E)`
- `pending`：实现了`PendingUpgrade`结构体，无论怎么poll它都返回`Poll::Pending`。类似的还有`ready`模块，无论怎么poll都**立即**返回`Poll::Ready`。
- `select`：实现一次性执行两个升级。

