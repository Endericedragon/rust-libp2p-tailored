# futures-bounded代码阅读笔记

该库在rust-libp2p的依赖图拓扑排序中被排在非常靠前的位置，因此可以作为第一个移植对象。为方便移植，我们来看看它的源代码吧。

## futures_?.rs系列

该系列首先实现了`futures_map.rs`，再以此为基础，实现了`futures_set.rs`和`futures_tuple_set.rs`。只需弄懂`futures_map.rs`，即可轻松弄懂后两者。

### futures_map.rs

## stream_?.rs系列