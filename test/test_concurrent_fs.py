import unittest
import threading
import time
from pathlib import Path

from nfs.fs.FileSystem import FileSystem
from nfs.fs.DirectoryNode import DirectoryNode
from nfs.fs.FileNode import FileNode

class TestFileSystem(unittest.TestCase):

    def setUp(self):
        # Setup a fresh file system before each test
        self.base_data_folder: str = "storage"
        self.fs = FileSystem(base_data_folder=self.base_data_folder)
        self.fs.create_directory('/dir1')

    def tearDown(self):
        # Clean up after each test
        # storage_dir = Path('storage')
        # if storage_dir.exists():
        #     for item in storage_dir.iterdir():
        #         if item.is_file():
        #             item.unlink()
        #         else:
        #             self._remove_dir(item)
        #     storage_dir.rmdir()
        pass

    def _remove_dir(self, dir_path):
        for item in dir_path.iterdir():
            if item.is_file():
                item.unlink()
            else:
                self._remove_dir(item)
        dir_path.rmdir()

    def test_create_file_concurrently(self):
        """Test if file creation is properly synchronized with thread locking"""
        
        def create_file_thread_1(self, file_path: str, content: str):
            """Function to be run by each thread to create a file"""
            file = self.fs.create_file(file_path, content)
            self.assertTrue(Path(self.fs.base_data_folder).joinpath(file.file_id).exists())
        
        def create_file_thread_2(self, file_path: str, content: str):
            """Function to be run by each thread to create a file"""
            with self.assertRaises(FileExistsError):
              file = self.fs.create_file(file_path, content)
              self.assertTrue(Path(self.fs.base_data_folder).joinpath(file.file_id).exists())

        # Start two threads that will attempt to create the same file concurrently
        thread1 = threading.Thread(target=create_file_thread_1, args=(self, '/dir1/file1.txt', 'Content from thread 1'))
        thread2 = threading.Thread(target=create_file_thread_2, args=(self, '/dir1/file1.txt', 'Content from thread 2'))
        
        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # After both threads finish, check that the file exists and check its content
        content = self.fs.get_file("/dir1/file1.txt")
        self.assertEqual(content, b'Content from thread 1') 

    def test_delete_file_concurrently(self):
        """Test if file deletion is properly synchronized with thread locking"""
        
        data: str = "Some content to delete"
        self.fs.create_file("/dir1/file_to_delete.txt", data)
        content = self.fs.get_file("/dir1/file_to_delete.txt")
        self.assertEqual(bytes(data, 'utf-8'), content)
        
        def delete_file_thread_1(self, file_path: str):
            """Function to be run by each thread to delete a file"""
            self.fs.delete_file(file_path)
            with self.assertRaises(FileNotFoundError):
              self.fs.root.children['dir1'].delete_file('file_to_delete.txt')


        def delete_file_thread_2(self, file_path: str):
            """Function to be run by each thread to delete a file"""
            with self.assertRaises(FileNotFoundError):
              self.fs.delete_file(file_path)
              self.fs.root.children['dir1'].delete_file('file_to_delete.txt')
          
        # Start two threads that will attempt to delete the same file concurrently
        thread1 = threading.Thread(target=delete_file_thread_1, args=(self, '/dir1/file_to_delete.txt'))
        thread2 = threading.Thread(target=delete_file_thread_2, args=(self, '/dir1/file_to_delete.txt'))
        
        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # After both threads finish, the file should be deleted, and accessing it should raise an exception
        with self.assertRaises(FileNotFoundError):
            self.fs.get_file("/dir1/file_to_delete.txt")

if __name__ == '__main__':
    unittest.main(verbosity=2)
