# libp2p-core代码结构速览

在`cargo metadata`中的标记为`path+file://.../rust-libp2p-pg/core#libp2p-core@0.39.1`。从名字和文档中不难推断出，`core`库是libp2p的核心模块，而从`Cargo.toml`中的记载来看，本库定义了rust-libp2p的核心trait和结构体。

根据仓库readme的说法，几乎所有rust-libp2p的实现都依赖于本库。观察本库的依赖项，会发现它有`libp2p-identity`、`multistream-select`和`rw-stream-sink`三个指向代码仓库中的相对路径的依赖项。这说明`core`库并非整个代码仓库的依赖树的根，它在依赖树上还有父节点。有关这三个库的代码结构速览，请见<a href="../identity/note.md" target="_self">libp2p-identity代码结构速览</a>、<a href="../misc/multistream-select/note.md" target="_self">multistream-select代码结构速览</a>和<a href="../misc/rw-stream-sink/note.md" target="_self">rw-stream-sink代码结构速览</a>三节。