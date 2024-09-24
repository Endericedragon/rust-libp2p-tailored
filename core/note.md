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

其核心在于`StreamMuxer` trait。若某个`struct A`实现了`StreamMuxer`，那么它一定拥有一个连接（connection），并且有能力将这个连接细分为多个子数据流（substream）。

一个连接中的子数据流互相独立，互不影响，且可以使用不同的协议。

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

## peer_record

## signed_envelope

## upgrade
