# Lab Report for NFS Lab

## A 

## Running ZooKeeper on Docker

```
docker pull
```

### [Experiment 1] ZooKeeper Demo

![](./images/zk_demo_1.png)

- 

### [Experiment 2]

## Testing

### Unit-testing

Run the following command to begin unit-testing:
```shell
python -m untitest discover test -v
```

Tested modules:
- [ ] File System \(`nfs.fs`\)
  - [x] File Node \(`nfs.fs.FileNode`\)
  - [x] Directory Node \(`nfs.fs.DirectoryNode`\)
- [ ] Server methods
  - [ ] Open
  - [ ] Close
  - [ ] Write
  - [ ] Read 
  

## References

- https://zookeeper.apache.org/doc/r3.4.5/zookeeperStarted.html#sc_Download
- https://hub.docker.com/_/zookeeper