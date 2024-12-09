export LD_LIBRARY_PATH=$(rustc --print sysroot)/lib:$LD_LIBRARY_PATH
echo $LD_LIBRARY_PATH
# export PTA_LOG=info
cargo clean
# /home/endericedragon/repos/rupta/target/release/cargo-pta pta --release -- --entry-func main --dump-call-graph cg.dot
cargo-pta pta --release -- --dump-overall-metadata om.json
