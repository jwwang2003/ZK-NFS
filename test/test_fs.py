import unittest
import threading
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
        storage_dir = Path('storage')
        if storage_dir.exists():
            for item in storage_dir.iterdir():
                if item.is_file():
                    item.unlink()
                else:
                    self._remove_dir(item)
            storage_dir.rmdir()
        pass

    def _remove_dir(self, dir_path):
        for item in dir_path.iterdir():
            if item.is_file():
                item.unlink()
            else:
                self._remove_dir(item)
        dir_path.rmdir()

    def test_create_directory(self):
        """
        --- /
            |- dir1
            |- dir2
        """
        
        self.fs.create_directory('/dir2')
        dir2 = self.fs.root.children['dir2']
        self.assertIsInstance(dir2, DirectoryNode)
        self.assertEqual(dir2.name, 'dir2')
    
    def test_create_nested_directory(self):
        """
        --- /
            |- dir1
                |- dir2
        """
        
        self.fs.create_directory('/dir1/dir2')
        dir1 = self.fs.root.children['dir1']
        self.assertIsInstance(dir1, DirectoryNode)
        
        dir2 = dir1.children['dir2']
        self.assertIsInstance(dir2, DirectoryNode)
        self.assertEqual(dir2.name, 'dir2')
    
    def test_create_file(self):
        """
        --- /
            |- dir1
                |- test.txt
        """
        
        data: str = "some example content"
        self.fs.create_file("/dir1/test.txt", data)
        content = self.fs.get_file("/dir1/test.txt")
        self.assertEqual(bytes(data, 'utf-8'), content)

    def test_delete_file(self):
        """
        --- /
            |- dir1
                |- file1.txt
                |- file2.txt
        """
        
        data: str = "some example content"
        file1 = self.fs.create_file("/dir1/file1.txt", data)
        self.assertTrue(Path(self.fs.base_data_folder).joinpath(file1.file_id).exists())
        content = self.fs.get_file("/dir1/file1.txt")
        self.assertEqual(bytes(data, 'utf-8'), content)
        
        file2 = self.fs.create_file('/dir1/file2.txt', 'File to delete')
        self.assertTrue(Path(self.fs.base_data_folder).joinpath(file2.file_id).exists())
        content = self.fs.get_file("/dir1/file2.txt")
        self.assertEqual(b'File to delete', content)
        self.fs.delete_file('/dir1/file2.txt')
        with self.assertRaises(FileNotFoundError):
            self.fs.root.children['dir1'].delete_file('file2.txt')
        self.assertFalse(Path(self.fs.base_data_folder).joinpath(file2.file_id).exists())
    
    def test_delete_non_empty_dir(self):
        """
        --- /
            |- dir1
                |- file1.txt
        """
        
        data: str = "some example content"
        file1 = self.fs.create_file("/dir1/file1.txt", data)
        self.assertTrue(Path(self.fs.base_data_folder).joinpath(file1.file_id).exists())
        content = self.fs.get_file("/dir1/file1.txt")
        self.assertEqual(bytes(data, 'utf-8'), content)
        
        with self.assertRaises(EnvironmentError):
            self.fs.delete_directory("/dir1")
    
    def test_rename_directory(self):
        """
        --- /
            |- dir1
            |- dir2
        
        --- /
            |- dir1
            |- dir3
        """
        
        self.fs.create_directory('/dir2')
        dir2 = self.fs.root.children['dir2']
        self.assertIsInstance(dir2, DirectoryNode)
        self.assertEqual(dir2.name, 'dir2')
        
        self.fs.rename_directory("/dir2", "dir3")
        self.assertEqual(dir2.name, 'dir3')
    
    def test_rename_file(self):
        """
        --- /
            |- dir1
                |- file1.txt
                |- file2.txt
        
        --- /
            |- dir1
                |- file1.txt
                |- file3.txt
        """
        
        data: str = "some example content"
        file1 = self.fs.create_file("/dir1/file1.txt", data)
        self.assertTrue(Path(self.fs.base_data_folder).joinpath(file1.file_id).exists())
        self.assertTrue(isinstance(file1.file_path, Path))
        content = self.fs.get_file("/dir1/file1.txt")
        self.assertEqual(bytes(data, 'utf-8'), content)
        
        file2 = self.fs.create_file('/dir1/file2.txt', 'File to delete')
        self.assertTrue(Path(self.fs.base_data_folder).joinpath(file2.file_id).exists())
        content = self.fs.get_file("/dir1/file2.txt")
        self.assertEqual(b'File to delete', content)
        
        self.fs.rename_file("/dir1/file2.txt", "file3.txt")
        content = self.fs.get_file("/dir1/file3.txt")
        self.assertEqual(b'File to delete', content)

if __name__ == '__main__':
    unittest.main(verbosity=2)
