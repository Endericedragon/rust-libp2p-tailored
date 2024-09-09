# rust-libp2p学习笔记

本文档记录笔者学习rust-libp2p的过程。

当前正在研究的版本是`0.51.3`。一些可能用到的链接罗列如下：

- [libp2p官网](https://libp2p.io/)
- [libp2p实现简介](https://libp2p.io/implementations/)
- [rust-libp2p](https://docs.rs/libp2p/0.51.3/libp2p/index.html)
- [Rust语言圣经 - 异步编程](https://course.rs/advance/async/intro.html)

当前阶段的任务是：

- [ ] 大致了解rust-libp2p的概况
- [ ] 写一个p2p程序，熟悉其使用
- [ ] 了解它的模块化构造，并切分过大的模块为更小的模块

## rust-libp2p概况

libp2p是一个开源的p2p网络协议栈，自称囊括了对发布-订阅（pub-sub）消息传递、分布式哈希表、NAT穿透（NAT hole punching）和浏览器到浏览器的直接通信的支持。libp2p有很多语言的实现，包括但不限于Rust、Python、Go、JavaScript等。