#!/usr/bin/env python

'''
This module defines the FileNode class for simulating a basic file in a virtual file system.
It provides functionality to create, rename, modify, and manage files, as well as generate unique identifiers for them.

The FileNode represents a file with associated content, file path, and metadata, such as creation and modification timestamps.
Note that the file content is stored in memory (or could be saved to disk if extended) and managed through the `file_path`.

Main features include:
- Creating and managing files using nodes.
- Renaming files and updating their metadata.
- Modifying file content and updating the modification timestamp.
- Generating unique file IDs using file name and content.
- Retrieving the file path and metadata (timestamps).
'''

__author__          = "JUN WEI WANG"
__copyright__       = "Copyright 2025"
__credits__         = ["JUN WEI WANG"]
__license__         = "GPL"
__version__         = "1.0.0"
__maintainer__      = "JUN WEI WANG"
__email__           = "wjw_03@outlook.com"

import hashlib
import time
from pathlib import Path

class FileNode:
    def __init__(self, name: str, file_path: Path):
        self.name: str = name                   # File name
        self.file_path: Path = file_path        # Virtual file path
        
        self.file_id: str = self.generate_file_id()
        
        # Some metadata
        self.size: int = 0
        self.created_at = time.time()
        self.modified_at = time.time()

    def get_file_path(self) -> Path:
        return self.file_path

    def generate_file_id(self) -> str:
        """Generate a unique file ID based on file name and content (hash)"""
        file_hash = hashlib.sha256(f"{self.name}{self.file_path}".encode()).hexdigest()
        return file_hash

    def rename(self, new_name: str):
        """Rename the file and update the file metadata"""
        self.name = new_name
        self.file_id = self.generate_file_id()
        self.file_path = Path.joinpath(self.file_path.parent, new_name)
        self.modified_at = time.time()
    
    def move(self, path: Path) -> 'FileNode':
        """Move the file to another path"""
        if not isinstance(path, Path):
            path = Path(path)
        
        self.file_path = path
        self.file_id = self.generate_file_id()
        self.file_path = Path.joinpath(self.file_path.parent, self.file_path.name)
        self.modified_at = time.time()

    def __str__(self):
        return f"File: {self.name}\nSize: {self.size}\nPath: {self.file_path}\nFile ID: {self.file_id}\nCreated: {time.ctime(self.created_at)}\nModified: {time.ctime(self.modified_at)}"
    
    def __repr__(self):
        return f"FileNode(name={self.name}, file_id={self.file_id}, file_path={self.file_path}, created_at={self.created_at}, modified_at={self.modified_at})"
    
    # Serialization method (pickling)
    def __getstate__(self):
        """
        This method is called when pickling the object. 
        It returns the object's state as a dictionary.
        """
        state = self.__dict__.copy()
        # If file_path is a Path object, convert it to a string for serialization
        state['file_path'] = str(self.file_path)
        return state

    # Deserialization method (unpickling)
    def __setstate__(self, state):
        """
        This method is called when unpickling the object. 
        It restores the object's state from the dictionary.
        """
        state['file_path'] = Path(state['file_path'])  # Convert file_path back to a Path object
        self.__dict__.update(state)