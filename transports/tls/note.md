# libp2p-tls研究计划

编译到这个库的时候，由于它依赖了 `ring-0.16.20` ，而后者的一堆代码都是C甚至汇编写成的，和指令集平台强绑定，也不支持riscv，因此需要想办法将其改造或者替换掉。

目前的计划是：

- [x] 搞到 `ring-0.16.20` 的代码仓库，已经搞到了，在 [这个仓库](git@github.com:Endericedragon/ring.git) 的 `b/0.16` 分支上
- [ ] 看看这个库到底依赖了 `ring-0.16.20` 的哪些机能，正在进行中
- [ ] 将 `ring-0.16.20` 精简后，尝试进行移植，并测试是否能正常工作

## 本库依赖ring-0.16.20的机能

- `ring::signature`，用到它的源代码如下：
  - `transports/tls/src/certificate.rs`

没了。就这么简单。

Rupta可以根据DefId来确定它研究的入口函数，而DefId可以通过 `cargo rustc -- -Z unpretty=thir > thir.txt` 命令，从THIR中获取。
