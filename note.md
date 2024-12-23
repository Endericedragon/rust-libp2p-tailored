# rust-libp2p学习笔记

本文档记录笔者学习rust-libp2p的过程。

当前正在研究的版本是`0.53.2`。一些可能用到的链接罗列如下：

- [libp2p官网](https://libp2p.io/)
- [libp2p实现简介](https://libp2p.io/implementations/)
- [libp2p文档](https://docs.libp2p.io/concepts/introduction/overview/)
- [rust-libp2p](https://docs.rs/libp2p/0.51.3/libp2p/index.html)
- [Rust语言圣经 - 异步编程](https://course.rs/advance/async/intro.html)
- [go-libp2p简介](https://cloud.tencent.com/developer/article/1988253)

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
- `muxers/`: 是libp2p-core的StreamMuxer接口（原文作interface，笔者猜测应该体现为rust trait）的实现。例如在连接（特别是TCP连接）之上建立的 (sub)stream multiplexing protocols。Multiplexing protocols are (mandatory) Transport upgrades.
- `swarm/`: 实现了libp2p-core中定义的NetworkBehaviour和ConnectionHandler的中央接口（central interface）。这两个接口用于实现应用层协议，详见`protocols/`。
- `protocols/`: 基于libp2p-swarm的API实现的应用层协议。
- `misc/`: 提供各种杂项机能的库（Utility libraries）。
- `libp2p/examples/`: 一些示例，展示内置的应用层协议（详见`protocols/`）在典型的Transpot配置下是如何使用的。

## ring 版本升级计划

[这个issue](https://github.com/briansmith/ring/issues/1765) 已经证明， ring v0.17 及以上即可适配 riscvgc64-unknown-linux-gnu 平台。因此，需要将 rust-libp2p 对 ring v0.16.20 的依赖升级到 v0.17.5 。选择这个版本的原因是， rust-libp2p v0.53.2 已经依赖 ring v0.17.5 。

已经完成 "ring版本升级" 改造的模块有：

- transports/tls#libp2p-tls@0.3.0 （升级ring）
- transports/quic#libp2p-quic@0.10.2 （升级ring）
- webrtc-dtls v0.8.0 （整体升级到0.9.0）

正在施工的模块是：[sct@0.7.0](registry+https://github.com/rust-lang/crates.io-index#sct@0.7.0) 。

### rcgen 0.11.3 改造记录

一个改变是 `EcdsaKeyPair::from_pkcs8` 。[旧版函数签名](https://docs.rs/ring/0.16.20/ring/signature/struct.EcdsaKeyPair.html#method.from_pkcs8) 和 [新版函数签名](https://docs.rs/ring/0.17.5/ring/signature/struct.EcdsaKeyPair.html#method.from_pkcs8) 的对比说明了变化，新版将原本作为局部变量的 `rng` 改为了方法参数。参考旧版的写法补全即可。

另一个变化则在于 ring 的接口变化。对于类型 `ring::error::KeyRejected` ，原本的 `description_` 方法在 v0.17 中被移除了。因此，需要用 `unsafe` 块 获取错误信息。

```rust
impl From<ring::error::KeyRejected> for RcgenError {
	fn from(err: ring::error::KeyRejected) -> Self {
		let bruh: &'static str;
		unsafe {
			bruh = *(&err as *const KeyRejected as *const &'static str);
		}
        // 原来是RcgenError::RingKeyRejected(err.description_())
		RcgenError::RingKeyRejected(bruh)
	}
}
```

还有一个变化，rcgen依赖了自己的webrtc库，而这个webrtc库和我们本地的webrtc库虽然版本一样，但Cargo不这么认为。因此最终还是把rcgen中的依赖改成了本地的依赖，冲突问题才算解决。

### sct@0.7.0 改造记录

该库本身的改造非常简单，但其上级依赖（webrtc-dtls@0.9.0）非常变态。值得注意的是，若使用 nightly-2024-02-03 编译，将会出现 unstable feature 和 unknown feature 的警告。此时，使用更新的 nightly-2024-05-02 版本即可通过编译。此外，webrtc-dtls@0.9.0 库的 example 压根没法跑，一跑就提示 `hub` 找不着，关键是找遍了 Cargo.toml 也没找着这个 `hub` 究竟是何方神圣，因此笔者直接删除了所有 example ，总算是通过了编译并跑通了所有 tests 。

## 名词解释

`multiaddr`：一种用来标识终端网络地址的方法，类似于这个样子：`/ip4/127.0.0.1/tcp/1234/p2p/Qmcgpsy`。可以看到它包含的信息十分丰富，不仅包含IPv4地址，还包含了端口号、p2p协议的标识符等信息。

`multistream-select`：一种用于协议协商的协议。通信双方使用这个协议协商出之后通信使用的协议，然后采用那个协议进行下一步通讯。这样做的好处是，可以让libp2p支持尽可能多的协议，而且不会引起不知道用哪个协议的混乱。

`Stream Multiplexing`：一种复用数据流（Stream）的方法，能够在一个流上创建很多虚拟的子流，提高流的使用效率，其效果有点类似于CPU的多进程，每个进程都感觉自己独占了CPU，尽管实际上CPU核心就那么几个。详情请参阅[Multistream Overview](https://docs.libp2p.io/concepts/multiplex/overview/)。