# Network File System (NFS) Lab

A simple (non-robust) NFS implementation in Python using ZooKeeper for the distributed systems (分布式系统) course (COMP130123) at Fudan. Just a proof concept as it only supports simple file operations.

## Introduction

Main tasks of the lab:

* Implement a file system that supports the following operations: `open`, `read`, `write`, and `close`.
* Implement an NFS server node and an NFS client.
* Learn how to set up and use ZooKeeper.
* Use TCP-based communication between the server and client.
* Implement a file locking mechanism.
* Ensure that parallel clients do not interfere with each other (i.e., multiple clients can concurrently open and close the same or different files without conflict).

## How to run

Start the ZooKeeper backend:
```
docker compose up
```

To start a NFS server:
```
python -m nfs.server
```

To start a NFS client:
```
python -m nfs.client
```

To start the ZooKeeper Client CLI:
```
./run_client.sh
```

Or, you can run the following make scripts to get all the services up and running
```
make clean
make docker
make
```

## Running ZooKeeper on Docker

```
docker pull
```

## Methodology / Implementation

### Server and Client Communication via TCP WebSockets

The communication between the **NFS server** and **NFS client** happens over **TCP WebSockets**. This enables real-time, bidirectional communication, which is crucial for file system operations. WebSockets provide low-latency, full-duplex communication, ideal for the continuous flow of data between the client and the server.

#### **Client to Server Communication:**

1. **Client Commands**: The client sends specific commands to the server, such as `open`, `read`, `write`, and `close`. These commands are encoded into JSON format and sent over the WebSocket connection.
2. **Server Responses**: The server processes the command and returns a JSON response to the client. Responses include success/failure messages and, in the case of `open`, `read`, or `write`, the file metadata (`FileNode`) or file data itself.
3. **WebSocket Handling**: The `websockets` library is used on both the client and server to handle WebSocket communication. The server listens for incoming WebSocket connections on two ports:

   * One for handling **NFS commands** (`NFS_PORT`).
   * One for handling **binary file data transfer** (`NFS_FS_PORT`).

#### **Server Side Communication:**

* The server decodes incoming requests from the client and processes them:

  * **`open`**: Checks if the file exists, acquires a lock, and sends file metadata back to the client.
  * **`read`**: Sends the requested file data to the client.
  * **`write`**: Receives data to update the file and writes the changes.
  * **`close`**: Commits the changes and releases the lock.

#### **Client Side Communication:**

* The client sends commands like `open`, `read`, `write`, and `close` to the server. Each of these requests triggers a corresponding handler on the server to process the command.
* For `open`, the client receives a file metadata object (`FileNode`) and caches the file locally. For `read`, the client accesses the locally cached file. For `write`, the client writes to the local file and updates it on the server when closing the file.

---

### File Locking Mechanism via ZooKeeper

The **ZooKeeper** service is used to manage file locks, ensuring that only one client can access a file at a time. This avoids race conditions and ensures consistency between multiple clients accessing the same file.

#### **Locking Process Overview:**

1. **Acquiring a Lock**:

   * When the client wants to open a file, it first attempts to acquire a **lock** on the file by interacting with **ZooKeeper**.
   * The lock is implemented as an **ephemeral node** in ZooKeeper. Ephemeral nodes automatically disappear when the client disconnects, ensuring that the lock is released if the client crashes or disconnects unexpectedly.
   * If the lock is already held by another client, the requesting client must wait until the lock is released.

2. **Releasing the Lock**:

   * Once the client finishes its operations (e.g., after `write` or `close`), it sends a request to **ZooKeeper** to release the lock.
   * This ensures that the next client can acquire the lock and perform file operations without conflict.

3. **Lock Checking**:

   * Before performing operations like `open`, `write`, or `close`, the client checks if the file is locked by another client. If the lock is held, the client will either wait or abort the operation.

#### **ZooKeeper Manager Class**:

* The `ZooKeeperManager` class is responsible for acquiring, releasing, and checking locks. It uses the **KazooClient** from the **Kazoo library** to interact with ZooKeeper.
* Methods include:

  * **`acquire_lock`**: Creates an ephemeral lock node in ZooKeeper.
  * **`release_lock`**: Deletes the lock node when the client is done.
  * **`is_locked`**: Checks if the lock node exists, indicating that the file is currently locked.

---

### File Opening and Closing Process: Step-by-Step

#### **1. Opening a File (Client-Side)**:

1. **Send `open` Command**: The client sends an `open` command to the server with the path of the file to be opened.
2. **Check Lock**: The server checks if the file is locked. If it is locked by another client, the server waits or rejects the request.
3. **Acquire Lock**: If the file is not locked, the server acquires the lock via ZooKeeper and confirms the file's metadata.
4. **Send File Metadata**: The server sends a response with the file metadata (`FileNode`) back to the client.
5. **Cache File Locally**: The client receives the file metadata and caches the file locally for further operations (read/write).
6. **Send Read Request**: The client sends a read request to the server to get the file data, which is cached locally for use.

#### **2. Reading a File (Client-Side)**:

1. **Access Cached File**: The client does **not** need to send a `read` request to the server unless the file is not cached.
2. **Use Local Cache**: The client directly reads the file from its local cache, avoiding any unnecessary server communication.
3. **File Data**: If the file was read from the server, it would be cached for future use.

#### **3. Writing to a File (Client-Side)**:

1. **Write Locally**: The client writes the file **locally** to its cached copy, without sending a `write` request to the server initially.
2. **Buffer Changes**: The client accumulates changes to the file in its local cache until the `close` command is issued.

#### **4. Closing a File (Client-Side)**:

1. **Send `close` Command**: The client sends a `close` command to the server along with the file metadata (`FileNode`).
2. **Update Server**: The server updates the file content and metadata based on the changes made by the client.
3. **Flush Buffer**: The server flushes any buffered data to ensure all changes are written to the file. This step prevents issues with stale data.
4. **Release Lock**: After the file is successfully updated, the client releases the ZooKeeper lock and proceeds to unlock the file.
5. **File Closure**: The server marks the file as closed, and the client deletes its local cached copy of the file.

---

### Operation Flow

1. **Open a File**:

   * The client requests to open the file. The server checks if the file exists, acquires a lock via ZooKeeper, and sends metadata back to the client.
   * The client sends a read request to the server and gets a file response back.
   * The file is cached locally on the client.

2. **Read a File**:

   * The client **does not** send a read request to the server; instead, it reads the locally cached file.
   * The server sends the file data back to the client, and the client caches the data locally.

3. **Write to a File**:

   * The client writes to the local file and does **not** send anything to the server.

4. **Close the File**:

   * The client sends a `close` and `write` request, and the server updates the file content and metadata.
   * Once the file has successfully been updated, the client proceeds to unlock the file.
   * The server must flush the file buffer; otherwise, it might cause problems with incomplete data.
   * The lock is released, and the file is marked as closed.

## Testing

Run the following command to begin unit-testing:
```shell
python -m untitest discover test -v
```

Tested modules (unittest):
- [x] File System \(`nfs.fs`\)
  - [x] File Node \(`nfs.fs.FileNode`\)
  - [x] Directory Node \(`nfs.fs.DirectoryNode`\)
- [x] Server methods \(hand tested\)
  - [x] Open \(hand tested\)
  - [x] Close \(hand tested\)
  - [x] Write \(hand tested\)
  - [x] Read \(hand tested\)

### [Experiment 1] ZooKeeper Demo

![](./images/zk_demo_1.png)

**Executed Steps and Results:**

1. **Client Connection Initialization**:

   * The client connects to ZooKeeper using the server address `127.0.0.1:2181`. Several informational messages appear indicating that the connection is being established, the session is initiated, and TLS is disabled.
   * **Result**: Connection successfully established with ZooKeeper.

2. **Listing Root Path**:

   * The `ls /` command is executed, listing the root path in ZooKeeper.
   * **Result**: The root path (`/`) is empty, as indicated by the result `[]`.

3. **Creating a Node**:

   * A new node `zk_test` is created with the data `some_test_data` using the command `create /zk_test some_test_data`.
   * **Result**: The node `zk_test` is successfully created and the output confirms this with the message `Created /zk_test`.

4. **Listing Nodes**:

   * The `ls /` command is executed again to list the contents of the root path.
   * **Result**: The node `zk_test` appears in the root path, as expected.

5. **Getting Data from Node**:

   * The `get /zk_test` command is executed to retrieve the data stored in the `zk_test` node.
   * **Result**: The data `some_test_data` is successfully retrieved from the node `zk_test`.

6. **Setting Data in Node**:

   * The `set /zk_test junk` command is executed to modify the data of the `zk_test` node to `junk`.
   * **Result**: The data is successfully updated, but no confirmation message appears in the output.

7. **Getting Updated Data**:

   * The `get /zk_test` command is executed again to retrieve the updated data from the node.
   * **Result**: The data is now `junk`, confirming that the update was successful.

8. **Deleting a Node**:

   * The `delete /zk_test` command is executed to remove the `zk_test` node.
   * **Result**: The node is successfully deleted, as indicated by the output message `Deleted /zk_test`.

9. **Attempt to Get Deleted Node**:

   * The `get /zk_test` command is executed again to check the data of the deleted node.
   * **Result**: The node no longer exists, and the message `Node does not exist: /zk_test` is displayed.

This experiment demonstrates the basic functionality of ZooKeeper CLI commands:

* Creating, reading, updating, and deleting nodes.
* Verifying that a deleted node is no longer accessible.
  The steps executed confirmed that ZooKeeper can manage data nodes and handle basic operations, including node creation, modification, retrieval, and deletion.

## [Experiment 2] Verifying & demoing NFS

A `Makefile` is provided to streamline launching the Docker container, NFS server, and client:

1. **`make clean`**  — removes any leftover data.
2. **`make tests`**  — runs unit tests for every Python module.
3. **`make docker`**  — starts the ZooKeeper container (if it fails to launch, restarting the Docker engine usually resolves the issue).
4. **`make`**  — launches both the NFS server and client.

A helper script is also available for the ZooKeeper shell client:

```bash
./run_client.sh
```

Running the script opens the ZooKeeper CLI and connects to the active local instance, just as in Experiment 1.

---

### ZooKeeper Docker Container

![](./images/demo1/docker1.png)
![](./images/demo1/docker2.png)

### ZooKeeper Shell Client

![](./images/demo1/zk_shell.png)

---

### Demonstration

1. **Start the server, then open the client.**
   With the server running (left pane), launch the client shell with `python -m nfs.client` or simply run `make`.
   ![](./images/demo1/nfs_client1.png)

   * We open `file.txt` with `open`. If the file does not exist, the server creates it automatically.
   * Messages in **blue** are server responses, lines in **yellow** show `FileNode` metadata, and all other text is client-side output.
   * Because the server is initially empty, the file is empty as well (observe the result of `read` and the file size).
   * At first open, the server creates an empty file, which the client downloads and **caches locally**. Subsequent `read` and `write` commands affect only this cached copy and do not contact the server.

2. **Write data to the file.**
   ![](./images/demo1/nfs_client2.png)

   * We issue `write` to store `"Hello, world!"` in the open file.
   * Running `read` confirms the contents—the raw bytes, hex dump, and UTF-8 string are displayed.
   * These operations modify only the local cache; nothing has yet been committed to the server.

3. **Close the file to commit changes.**
   ![](./images/demo1/nfs_client3.png)

   * Executing `close` flushes the cached file back to the server. ZooKeeper releases the lock, and the server sends two confirmation messages (blue).
   * The final response includes updated `FileNode` metadata (yellow); note the increased file size and new modification timestamp.

4. **Re-open the file to verify persistence.**
   ![](./images/demo1/nfs_client4.png)

   * Opening the file again shows the same metadata as after the previous `close`.
   * Reading the file returns the data written earlier, confirming that the commit succeeded.
   * Closing the file now completes instantly because no further changes were made.

This sequence demonstrates that local caching, server commits, and ZooKeeper-based locking all operate correctly.

#### Aside

Let's take a look at the inner-workings of the ZooKeeper file lock mechanism that was implemented. The following shows a demo of the state of the ZooKeeper instance as a file was being opened and closed on the client side.

![](./images/demo1/zk_shell1.png)

During the process of opening and closing a file, a "lock" is created or deleted from the ZooKeeper instance using the zk Python module. The screenshot above was taken after a new file was opened. From the image, we can observe that:

* An entry named `file.txt` was created at the root of the ZooKeeper instance.
* Inside this entry (`ls /file.txt`), there is a "lock".

![](./images/demo1/zk_shell2.png)

This screenshot shows the contents of the `file.txt` entry after the file was closed by the client. Now, the "lock" file has disappeared, indicating that no one currently has the file open.

This confirms that our implemented locking mechanism for the NFS is functioning as expected.


### Problem with two clients opening the same file

Screenshots of the bug:

![](./images/demo1/bug/1.png)
![](./images/demo1/bug/2.png)
![](./images/demo1/bug/3.png)

The error is caused by the file size between the data received from the server and the file node size data not matching.

**Before:**

```python
async def handle_open(self, command):
    parts = shlex.split(command)
    if not len(parts) == 2:
        print("open takes one argument.")
        return

    parts = parts[1:]
    
    file_path = parts[0]
    
    openRequest = OpenRequest()
    response = await self.websocket_comm(
        nfs_server_uri,
        openRequest.encode(Path(file_path))
    )
    
    openResponse = OpenResponse()
    openResponse.decode(response)
    
    if not openResponse.OK:
        print(colored(openResponse.message, "red"))
        return
    
    if not await self.lock(FileNode("", Path(file_path))):
        return
    
    print(colored(openResponse.message, "light_blue"))
    ...

async def lock(self, file_node: FileNode) -> bool:
    # Check if a file is already opened
    if (not self.current_file_node == None) and (not self.current_zk_lock == None):
        print("A File a already opened! Please close it first.")
        return False
    elif (not self.current_file_node == None) or (not self.current_zk_lock == None):
        print("A File was opened? Current tracker got corrupted, resetting...")
        self.current_file_node = None
        self.current_zk_lock = None
    
    try:  
        self.current_file_node = file_node
        await self.zk_lock(self.current_file_node.file_path.as_posix())
        assert not self.current_file_node == None and not self.current_zk_lock == None
    except AssertionError as e:
        print(f"An error occured while locking file: {e}")
        return False

    return True
```

**After:**

```python
async def handle_open(self, command):
    parts = shlex.split(command)
    if not len(parts) == 2:
        print("open takes one argument.")
        return

    parts = parts[1:]
    
    file_path = parts[0]
    
    if not await self.lock(FileNode("", Path(file_path))): # changed
        return
    
    openRequest = OpenRequest()
    response = await self.websocket_comm(
        nfs_server_uri,
        openRequest.encode(Path(file_path))
    )
    
    openResponse = OpenResponse()
    openResponse.decode(response)
    
    if not openResponse.OK:
        print(colored(openResponse.message, "red"))
        return
    
    self.current_file_node = openResponse.file_node # changed
    
    print(colored(openResponse.message, "light_blue"))
    ...

async def lock(self, file_node: FileNode) -> bool:
    # Check if a file is already opened
    if (not self.current_file_node == None) and (not self.current_zk_lock == None):
        print("A File a already opened! Please close it first.")
        return False
    elif (not self.current_file_node == None) or (not self.current_zk_lock == None):
        print("A File was opened? Current tracker got corrupted, resetting...")
        self.current_file_node = None
        self.current_zk_lock = None
    
    try:
        # changed
        await self.zk_lock(file_node.file_path.as_posix())
        assert not file_node == None and not self.current_zk_lock == None
    except AssertionError as e:
        print(f"An error occured while locking file: {e}")
        return False

    return True
```


In summary, the bug was caused by a combination of logic implemented in the wrong order in the `open` handler on the client and the `write` handler on the server. For the former, we have to modifiy the `handle_open` method and move the file lock acquisition to the top before any command it sent to the server. For the latter, the server should always flush the buffer before returning and sending a response back to the client to ensure that the data is actually written. If not, then the next request might get data that is stall or not up-to-date.

## Experiment 3

In this experiment, we test the file locking mechanism and parallel processing features of the NFS server. The following tests will be conducted:

* With two clients, open the **same file** at the same time.

  * The expected outcome is that one client would have to wait for the other one to release the lock.
  * Whichever client opens the file first and writes to it, the changes should properly reflect on the client that opens it afterward.
* Ensure that two clients writing to **different files** at the same time are handled properly.

### Two Clients Competing for the Same File

One of the most important features of NFS is the file locking mechanism. In this implementation, we use ZooKeeper to facilitate the locking mechanism. This experiment will validate and demonstrate the correctness of the mechanism.

1. With two clients connected to the NFS server, open the same file `file.txt` at the same time.
   ![](./images/demo2/1.1.png)

   * We observe that the middle window wins the competition and obtains the file node, while the right window loses and waits for the file lock to be released.
2. Write some data to the file and verify its contents.
   ![](./images/demo2/1.2.png)

   * The right window is still waiting for the file to be unlocked.
   * It is crucial here to realize that the file is being edited locally; nothing has been sent to the server yet.
3. The middle window executes the close command, the file node & file data are updated on the NFS server, and finally, the lock on `file.txt` is released.
   ![](./images/demo2/1.3.png)

   * We observe that the file node data shown in the middle window is correct.
   * The right window finally gets the file lock and proceeds to read the newly updated file from the server.
   * Notice how the file content is exactly as the middle window left it, confirming that the implementation works correctly (the bug experienced in experiment 2 is fixed).
4. The right window appends more data to `file.txt`, and the middle window tries to open `file.txt` while the right window has not yet closed it.
   ![](./images/demo2/1.4.png)

   * More data is successfully appended to the file in the right window.
   * The middle window is waiting for the file to be released.
5. Finally, the right window closes the file, and the server updates the new content. The middle window obtains the file lock and proceeds to read its content to verify consistency.
   ![](./images/demo2/1.5.png)

   * After the middle window regains the file lock, its data has been modified by the right window, confirming correctness.

Through this demo, we can see that when two clients attempt to open the same file simultaneously, only one of them will succeed and gain access to the file. The other client must wait for the lock to be released. This process relies on coordination between the client and the ZooKeeper instance. The server does not directly participate in the locking mechanism (though a more robust implementation might involve both server and client communication with ZooKeeper).

The demo successfully demonstrates that the file locking mechanism works because the right window had to wait for the middle window to close the file before accessing and retrieving data. Thus, this implementation is resilient to parallel file access. In the following experiment, we demonstrate the same scenario but with different files.

### Two Clients Opening Different Files

In this experiment, we will demonstrate that two clients can open and close two different files simultaneously. After closing the files, we can further verify correctness by exchanging the files between the clients to ensure the data remains valid.

1. In the middle window, `file1.txt` is opened, and data is written to the file. A read operation displays the updated information. Simultaneously, a new file `file2.txt` is opened in the right window, and data is appended to it.
   ![](./images/demo2/2.1.png)
2. After writing data to both files, we proceed to close them.
   ![](./images/demo2/2.2.png)
3. Now we open `file2.txt` in the middle window and `file1.txt` in the right window (exchanging their positions) to verify data consistency and correctness.
   ![](./images/demo2/2.3.png)

This demo illustrates that two (or multiple) clients can open and close files in parallel without conflict, provided the files are different. If the same file is accessed, clients must compete for the lock, and only one client can access it at a time. Other clients must wait for the lock to be released before retrying.

## Self-evaluation

### **NFS Server**

* **Correct implementation of open, read, write, close interfaces:**
  The report shows that the NFS server correctly implements the four file system operations (`open`, `read`, `write`, and `close`). The operations are carried out via WebSockets, where the client sends requests, and the server processes these requests accordingly. The implementation is clear and follows the expected behavior for file system operations.

* **Stable handling of multiple client concurrency:**
  The NFS server handles multiple clients effectively, with particular attention to the file locking mechanism. The report demonstrates that when two clients try to access the same file at the same time, one client must wait for the lock to be released by the other. This process is managed via ZooKeeper, ensuring there is no race condition or data corruption when handling concurrent requests. The system’s ability to handle parallel requests is properly showcased, including the scenario where two clients are accessing the same file.

### **Client**

* **Correct implementation of client interface and local caching:**
  The client implementation aligns with the requirements. It sends requests like `open`, `read`, `write`, and `close` to the server. Importantly, the client caches files locally after opening them, minimizing unnecessary interactions with the server when reading files. This helps improve performance and is a common strategy in file systems that aim to reduce server load. The report provides clear explanations on how the client interacts with the server and handles file data locally.

* **Implementation of at least two clients and validation of concurrent access:**
  The report validates the system's capability to handle at least two clients. It demonstrates scenarios where two clients can interact with the system simultaneously, ensuring that the NFS server handles concurrent file access properly. The use of ZooKeeper locks effectively manages these interactions, with only one client being able to modify a file at a time. This scenario was successfully demonstrated and validated, meeting the concurrency requirement.

### **ZooKeeper Locking Mechanism**

* **Correct configuration of ZooKeeper and /nfslk node:**
  The configuration and implementation of the ZooKeeper-based file locking mechanism are correctly explained. The lock is implemented using ephemeral nodes in ZooKeeper, ensuring that the lock is automatically released when a client disconnects. The `/nfslk` node, which serves as the lock for each file, is used correctly, and the report demonstrates how ZooKeeper handles the lock management process.

* **Implementation of distributed lock and correct locking/unlocking:**
  The implementation of the distributed lock mechanism is effective. The system uses ZooKeeper to ensure that only one client has access to a file at a time. The report outlines the steps involved in acquiring, releasing, and checking the lock. The `acquire_lock`, `release_lock`, and `is_locked` methods are implemented properly to prevent race conditions. This locking mechanism is crucial in maintaining consistency when multiple clients are accessing the same file, and the report shows that it works as expected.

## Conclusion

In this lab, we have implemented a simple yet effective Network File System (NFS) using Python and ZooKeeper. The implementation demonstrates key concepts in distributed systems, including file system operations such as `open`, `read`, `write`, and `close`, and crucial features like concurrency handling and file locking. By leveraging ZooKeeper’s distributed locking mechanism, the system ensures safe and synchronized access to files, preventing race conditions when multiple clients attempt to access the same file simultaneously.

The communication between the NFS server and clients is established over TCP WebSockets, facilitating real-time, bidirectional communication that is essential for efficient file operations. The report includes detailed descriptions of how the server and client interact, including caching files locally on the client to reduce server load and enhance performance. It also outlines how the server processes each operation and ensures the correct metadata and file content are returned to the client.

Testing and validation through experiments were performed to ensure that the system can handle concurrent client operations. The ZooKeeper-based locking mechanism was tested and demonstrated to function as expected, with the system correctly managing access to files by multiple clients. The report identifies and addresses a bug related to two clients accessing the same file, offering a clear explanation and solution for the issue.

Overall, the lab successfully meets the design objectives, providing a basic but functional proof of concept for an NFS system that can handle file operations and concurrency while ensuring data consistency through ZooKeeper. The system provides a solid foundation for further development and enhancement, with potential improvements in robustness and fault tolerance.

## References

- https://zookeeper.apache.org/doc/r3.4.5/zookeeperStarted.html#sc_Download
- https://hub.docker.com/_/zookeeper