from pathlib import Path
import json
import pickle

from nfs.fs import FileNode

class Template:
    def __init__(self):
        pass
    
    def encode(self):
        pass
    
    def decode(self, bytes: bytes):
        pass

class OpenRequest:
    '''
    {
        "action": "open",
        "file_path": "<path_to_file>"
    }
    '''
        
    def __init__(self):
        self.action: str = "open"
        self.file_path: Path = None
    
    def encode(self, file_path: Path) -> str:
        self.file_path = file_path
        data: str = json.dumps(
            {
                "action": "open",
                "file_path": self.file_path.as_posix(),
            }
        )
        return data
        
    def decode(self, bytes: bytes):
        decoded = bytes.decode('utf-8')
        obj = json.loads(decoded)
        try:
            self.action = obj['action']
            self.file_path = Path(obj['file_path'])
        except IndexError as e:
            print("Open request decoding error")

class OpenResponse:
    '''
    {
      "message": <string>,
      "file_node": <bytes>
    }
    '''
  
    def __init__(self):
        self.message: str = ""
        self.OK: bool = False
        self.file_node: FileNode = None
    
    def encode(self, msg: str = "", OK: bool = False, file_node: FileNode = None) -> str:
        data: str = json.dumps(
            {
                "message": msg,
                "OK": OK,
                "file_node": pickle.dumps(file_node).hex()
            }
        )
        return data
    
    def decode(self, bytes: bytes):
        decoded = bytes.decode('utf-8')
        obj = json.loads(decoded)
        try:
            self.message = obj['message']
            self.OK = obj['OK']
            self.file_node: FileNode = pickle.loads(bytes.fromhex(obj['file_node']))
        except IndexError as e:
            print("Open response decoding error")

class CloseRequest:
    def __init__(self):
        '''
        {
            "action": "close",
            "file_node": "<FileNode>"
        }
        '''
        self.action: str = "close"
        self.message: str = ""
        self.OK: bool = False
        self.file_node: FileNode = None
    
    def encode(self, file_node: FileNode = None) -> str:
        data: str = json.dumps(
            {
                "action": "close",
                "file_node": pickle.dumps(file_node).hex()
            }
        )
        return data
    
    def decode(self, bytes: bytes):
        decoded = bytes.decode('utf-8')
        obj = json.loads(decoded)
        try:
            self.action = obj['action']
            self.file_node = pickle.loads(bytes.fromhex(obj['file_node']))
        except IndexError as e:
            print("Close request decoding error")

'''
Once a file has successfully been updated, emit a global commit message to NFS server
with the new metadata. The NFS will then update the file node accordingly.
'''
class CloseResponse:
    def __init__(self):
        '''
        {
            "message": <string>,
            "OK": <bool>,
            "file_node": <bytes>
        }
        '''
        self.action: str = "close"
        self.message: str = ""
        self.OK: bool = False
        self.file_node: FileNode = None
    
    def encode(self, msg: str = "", OK: bool = False, file_node: FileNode = None):
        data: str = json.dumps(
            {
                "message": msg,
                "OK": OK,
                "file_node": pickle.dumps(file_node).hex()
            }
        )
        return data
    
    def decode(self, bytes: bytes):
        decoded = bytes.decode('utf-8')
        obj = json.loads(decoded)
        try:
            self.message = obj['message']
            self.OK = obj['OK']
            self.file_node: FileNode = pickle.loads(bytes.fromhex(obj['file_node']))
        except IndexError as e:
            print("Close response decoding error")

'''
Data transfer socket wrappers
'''

class ReadRequest:
    def __init__(self):
        '''
        {
            "action": "read",
            "file_node": <bytes>,
            "seek": <int>, (offset)
            "len": <int>, (bytes to read)
        }
        '''
        self.action: str = "read"
        self.file_node: FileNode = None
    
    def encode(self, file_node: FileNode = None) -> str:
        data: str = json.dumps(
            {
                "action": self.action,
                "file_node": pickle.dumps(file_node).hex()
            }
        )
        return data
    
    def decode(self, bytes: bytes):
        decoded = bytes.decode('utf-8')
        obj = json.loads(decoded)
        try:
            self.file_node = pickle.loads(bytes.fromhex(obj['file_node']))
        except IndexError as e:
            print("Download request decoding error")

class ReadResponse:
    def __init__(self):
        '''
        {
            "message": <str>,
            "file_node": <bytes>,
            "data": <bytes>
        }
        '''
        self.message: str = ""
        self.OK = False
        self.file_node: FileNode = None
        self.data: bytes = None
    
    def encode(self, msg: str = "", OK: bool = False, data: bytes = None) -> str:
        self.data = data
        data: str = json.dumps(
            {
                "message": self.message,
                "OK": OK,
                "file_node": pickle.dumps(self.file_node).hex(),
                "data":  pickle.dumps(self.data).hex(),
            }
        )
        return data
    
    def decode(self, bytes: bytes):
        decoded = bytes.decode('utf-8')
        obj = json.loads(decoded)
        try:
            self.message = obj['message']
            self.OK = obj['OK']
            self.file_node = pickle.loads(bytes.fromhex(obj['file_node']))
            self.data = pickle.loads(bytes.fromhex(obj['data']))
        except IndexError as e:
            print("Download response decoding error")

class WriteRequest:
    def __init__(self):
        '''
        {
            "action": "write",
            "file_node": <bytes>,
            "data": <bytes>
        }
        '''
        self.action: str = "write"
        self.file_node: FileNode = None
        self.data: bytes = None
    
    def encode(self, file_node: FileNode, data: bytes) -> str:
        data: str = json.dumps(
            {
                "action": self.action,
                "file_node": pickle.dumps(file_node).hex(),
                "data": pickle.dumps(data).hex()
            }
        )
        return data
    
    def decode(self, bytes: bytes):
        decoded = bytes.decode('utf-8')
        obj = json.loads(decoded)
        try:
            self.file_node = pickle.loads(bytes.fromhex(obj['file_node']))
            self.data = pickle.loads(bytes.fromhex(obj['data']))
        except IndexError as e:
            print("Upload request decoding error")

class WriteResponse:
    def __init__(self):
        '''
        {
            "message": <str>,
            "OK": <bool>,
            "file_node": <bytes>,
            "bytes_written": <int>
        }
        '''
        self.message: str = ""
        self.OK: bool = False
        self.file_node: FileNode = None
        self.bytes_written: int = -1
    
    def encode(self, msg: str = "", OK: bool = False, file_node: FileNode = None, bytes_written: int = -1) -> str:
        data: str = json.dumps(
            {
                "message": msg,
                "OK": OK,
                "file_node": pickle.dumps(file_node).hex(),
                "bytes_written": bytes_written
            }
        )
        return data
    
    def decode(self, bytes: bytes):
        decoded = bytes.decode('utf-8')
        obj = json.loads(decoded)
        try:
            self.message = obj["message"]
            self.OK = obj["OK"]
            self.file_node = pickle.loads(bytes.fromhex(obj['file_node']))
            self.bytes_written = obj["bytes_written"]
        except IndexError as e:
            print("Write response decoding error")