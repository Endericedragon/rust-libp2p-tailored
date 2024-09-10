# libp2p-identity代码结构速览

被<a href="../core/note.md" target="_self">libp2p-core</a>所依赖。该crate的作用，就是帮助libp2p在P2P网络中唯一地标识每一个节点。

> 插播：关于Rust中`#[cfg(...)]`的作用，该写法表示条件编译，即只有在编译条件满足时，才会编译该代码块。常见的条件有如下几种：
>
> - `target_os`：顾名思义，只在指定的目标系统下编译
> - `target_arch`：只在指定的架构下编译
> - `feature`：指定某个feature时开启编译
> - `all(cond1, cond2)`：同时满足多个条件 `cond1, cond2` 时编译，类似于`&&`
> - `any(cond1, cond2)`：满足任意一个条件 `cond1, cond2` 时编译，类似于`||`
> - `not(cond)`：不满足某条件 `cond` 时编译

总结该库的功能为：
1. 兼容四种密钥对协议，通过各种方法生成/重建密钥对，并提供签名和验证功能。
2. 实现了`PeerId`结构，用于唯一地标识一个节点。

## src/lib.rs

该源文件的作用较为简单，就是根据外部调用者给定的不同`feature`，暴露出不同的`mod`来。因为identity支持非常多种产生密钥对的协议（例如RSA、ED25519等），所以使用条件编译来消除多余的代码实为明智之举。它向外暴露了如下模块（`mod`）：

- ecdsa
- ed25519
- rsa
- secp256k1

除了暴露这些`mod`以外，它还使用了一些非公开的模块：

- proto
- peer_id
- keypair
- error

除上述所有工作外，它还做了两件事：

- 为`proto::PrivateKey`实现了`zeroize::Zeroize` trait。这个trait的作用很简单，就是将给定内存中的值全部清零，并且保证这个过程不会被编译器优化没了。
- 实现了从公钥`PublicKey`转换到内部使用的`proto::PublicKey`的`From` trait。在lib.rs文件的开头就提及，identity可以将各种不同协议的密钥对的二进制表示转换为统一的`proto::PublicKey`类型。

## src/generated中的`proto`模块

该目录下只有`keys.proto`和`mod.rs`是程序员写的，剩下的代码均由`quick-protobuf`自动生成。在`identity/src/lib.rs`中，被重命名为了`proto`模块。

Protobuf（Protocol Buffer）是一种和具体平台和编程语言均无关的可序列化数据结构协议，类似于JSON和XML，但是可以把定义好的Protobuf消息序列化为各个编程语言中的具体数据结构（例如Python的class，Rust中的struct等）。其信息载荷即为`Message`结构，定义好这个结构即可规定传输的信息的结构。

```proto
/* file: keys.proto */

// 指定使用proto2的语法。目前最新的是proto3
syntax = "proto2";
// 定义包名，可以看到它编译的结果就是keys_proto.rs
package keys_proto;

// 定义一个枚举，表示密钥对的协议类型
// 这里的数字只是确定枚举项的顺序
enum KeyType {
  // 0似乎有特殊的含义，似乎是默认的意思？
  RSA = 0;
  Ed25519 = 1;
  Secp256k1 = 2;
  ECDSA = 3;
}

// 定义一个消息，表示公钥
message PublicKey {
  // required表示必须字段，同理还有optional可选字段，但这儿没出现
  // 可以观察到，message中声明一个信息项的语法是：
  // required/optional <类型> <名称> = <序号>;
  required KeyType Type = 1;
  required bytes Data = 2;
}

// 定义一个消息，表示私钥
message PrivateKey {
  required KeyType Type = 1;
  required bytes Data = 2;
}
```

在这个`keys.proto`旁边的`keys_proto.rs`中，我们可以看到由`quick-protobuf`自动生成的Rust代码。基本都和`keys.proto`中的定义一一对应，并且为它们实现了从`BytesReader`中读，往`WriterBackend`中写的方法，这儿就不再赘述了。

## 密钥对协议模块：以ecdsa为例

作为第一个出场的密钥对协议，我们先来分析它。其核心结构是`Keypair`，包含一个`PublicKey`公钥和`SecretKey`私钥（分别由`p256::ecdsa::SigningKey`和`p256::ecdsa::VerifyingKey`包装得到），随后定义了用这个密钥对签名消息`&[u8]`的`sign`方法。

其他的密钥对协议模块和`ecdsa`类似，只是实现了不同的签名算法。这里就不再赘述。

## peer_id模块

该模块使用了两个比较陌生的模块，分别是用于处理多地址的`multiaddr`和处理多哈希的`multihash`。

> 多地址：用于描述网络地址的格式。例如，`/ip4/127.0.0.1/tcp/8080/p2p/QmExamplePeerId`表示IPv4地址127.0.0.1上的TCP端口8080，和P2P协议的标识符`QmExamplePeerId`。多地址允许将IP地址、端口、协议等信息编码为一个字符串（同时也允许反过来解析多地址字符串），方便在网络中传输。
>
> 多哈希：用于描述数据的哈希值，和多地址类似。例如，一个SHA-256哈希可以写为`<SHA-256标识符> <哈希值的长度> <哈希值本体>`。可以观察到，多哈希标注了自己所使用的哈希函数，因此具有自解释性。

有了上述前置知识，我们来探索一下`peer_id`模块吧。

第一个出场的是`PeerId`结构体，内含一个`multihash::Multihash`哈希值。这与`core`中的记录一致，即：`PeerId`用于唯一地标识一个节点。它实现了以下重点功能：

- 从公钥、字节流、multiaddr（原理：multiaddr的最后一节可能是`p2p/<peer-id的multihash>`）、其他multihash中或字符串中获得`PeerId`
- 凭空生成一个随机的新`PeerId`

## keypair模块

看上去似乎是个非常核心的模块。它定义了`Keypair`枚举，包含了密钥对协议模块中定义的四种协议的密钥对。在这个枚举上：
- 定义了随机、直接地创建这些密钥对的方法
- 定义了很多从不同类型的字节流上重建密钥对的方法，例如`rsa_from_pkcs8()`等
- 定义了签名方法
- 定义了和ProtoBuf互相转化的方法

为实现四种协议的兼容，它还定义了`PublicKey`枚举，除了常规的创建、转化以外，还实现了`verify()`方法。

## error模块

表示在处理密钥时可能发生的所有错误类型。

第一种错误表征为`DecodingError`结构，内含错误信息`msg`和错误发生源`source`。光讲有点抽象，来看个应用实例：

```rust
SigningKey::from_bytes(buf)
    .map_err(|err| DecodingError::failed_to_parse("ecdsa p256 secret key", err))
    .map(SecretKey)
```

这下很明白了，`msg`就是字符串类型的错误信息，而`source`就是诸如`std::io::Error`这样的Rust原生错误类型。

接下来，针对不同的错误，`DecodingError`准备了不同的构造函数用来提醒库用户。这些构造函数的唯一不同就是自身的`msg`被写入的的信息不同，例如`failed_to_parse()`是"failed to parse <具体信息>"，而`bad_protobuf()`输出"failed to decode <具体信息> from protobuf"。

第二种错误表征为`SigningError`结构，表示签名过程中的错误。其结构和`DecodeError`类似，只是`msg`和`source`的含义不同。其实现的方法也类似，故不再赘述。