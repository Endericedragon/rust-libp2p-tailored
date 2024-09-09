# rust-libp2p学习笔记

本文档记录笔者学习rust-libp2p的过程。

当前正在研究的版本是`0.51.3`。一些可能用到的链接罗列如下：

- [libp2p官网](https://libp2p.io/)
- [libp2p实现简介](https://libp2p.io/implementations/)
- [libp2p文档](https://docs.libp2p.io/concepts/introduction/overview/)
- [rust-libp2p](https://docs.rs/libp2p/0.51.3/libp2p/index.html)
- [Rust语言圣经 - 异步编程](https://course.rs/advance/async/intro.html)

当前阶段的任务是：

- [ ] 大致了解rust-libp2p的概况
- [ ] 写一个p2p程序，熟悉其使用
- [ ] 了解它的模块化构造，并切分过大的模块为更小的模块

## rust-libp2p概况

libp2p是一个开源的p2p网络协议栈，自称囊括了对发布-订阅（pub-sub）消息传递、分布式哈希表、NAT穿透（NAT hole punching）和浏览器到浏览器的直接通信的支持。libp2p有很多语言的实现，包括但不限于Rust、Python、Go、JavaScript等。请参见[libp2p文档](https://docs.libp2p.io/concepts/introduction/overview/)以更详细地了解libp2p项目。

## rust-libp2p代码仓库结构速览

本crate的代码结构较为复杂，因此计划按大模块进行逐一阅读分析。首先运行`cargo metadata`命令，然后浏览输出内容的`workspace_default_members`字段，即能知晓该仓库的默认成员。从它们开始入手研究本crate的代码结构较为稳妥。

根据官方文档的说法，该代码仓库的大致结构如下：

- `core/`: libp2p-core核心库的实现。包含了Transport 和 StreamMuxer API，几乎所有其他crate都依赖于它。
- `transports/`: 运输层协议的实现（例如TCP协议）和协议升级内容（protocol upgrades，例如用于认证加密、压缩等）。基于core库的Transport API实现。

`muxers/`: 是libp2p-core的StreamMuxer接口（原文作interface，笔者猜测应该体现为rust trait）的实现。例如在连接（特别是TCP连接）之上建立的 (sub)stream multiplexing protocols。Multiplexing protocols are (mandatory) Transport upgrades.

`swarm/`: 实现了libp2p-core中定义的NetworkBehaviour和ConnectionHandler的中央接口（central interface）。这两个接口用于实现应用层协议，详见`protocols/`。

protocols/: Implementations of application protocols based on the libp2p-swarm APIs.

misc/: Utility libraries.

libp2p/examples/: Worked examples of built-in application protocols (see protocols/) with common Transport configurations.

### libp2p-core代码结构速览

在`cargo metadata`中的标记为`path+file:///home/endericedragon/repos/rust-libp2p-pg/core#libp2p-core@0.39.1`。从名字中不难推断它是libp2p的核心模块。