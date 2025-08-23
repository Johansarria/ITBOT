import pytest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import logging

from utils.config_utils import update_env_file

@pytest.fixture(autouse=True)
def mock_logger():
    with patch('utils.config_utils.logger', new_callable=MagicMock) as mock_log:
        yield mock_log

@pytest.mark.asyncio
async def test_update_env_file_updates_existing_key(tmp_path):
    env_content = "KEY1=value1\nKEY2=old_value2\nKEY3=value3\n"
    env_path = tmp_path / ".env"
    env_path.write_text(env_content) # Create the actual file for os.path.exists

    key = "KEY2"
    value = "new_value2"
    
    # Mock os.path.exists to return True for the .env file
    with patch('os.path.exists', return_value=True):
        # Mock builtins.open to control file operations
        m_open = mock_open(read_data=env_content)
        with patch('builtins.open', m_open):
            result = await update_env_file(key, value)

            assert result is True
            
            # Assert open was called for reading and writing
            m_open.assert_any_call(".env", 'r')
            m_open.assert_any_call(".env", 'w')
            
            # Assert content written to file
            handle = m_open()
            handle.write.assert_any_call("KEY1=value1\n")
            handle.write.assert_any_call("KEY2=new_value2\n")
            handle.write.assert_any_call("KEY3=value3\n")

@pytest.mark.asyncio
async def test_update_env_file_adds_new_key(tmp_path):
    env_content = "KEY1=value1\nKEY2=value2\n"
    env_path = tmp_path / ".env"
    env_path.write_text(env_content) # Create the actual file for os.path.exists

    key = "NEW_KEY"
    value = "new_value"

    with patch('os.path.exists', return_value=True):
        m_open = mock_open(read_data=env_content)
        with patch('builtins.open', m_open):
            result = await update_env_file(key, value)

            assert result is True

            m_open.assert_any_call(".env", 'r')
            m_open.assert_any_call(".env", 'w')

            handle = m_open()
            handle.write.assert_any_call("KEY1=value1\n")
            handle.write.assert_any_call("KEY2=value2\n")
            handle.write.assert_any_call(f"\n{key}={value}\n")

@pytest.mark.asyncio
async def test_update_env_file_non_existent_file(tmp_path):
    # No need to create the file, os.path.exists will be mocked to False
    # env_path = tmp_path / ".env" # This path is not actually used by the mock_open

    key = "NEW_KEY"
    value = "new_value"

    with patch('os.path.exists', return_value=False):
        m_open = mock_open()
        with patch('builtins.open', m_open):
            result = await update_env_file(key, value)

            assert result is True
            # Only one call for writing
            m_open.assert_called_once_with(".env", 'w')
            handle = m_open()
            handle.write.assert_called_once_with(f"\n{key}={value}\n")

@pytest.mark.asyncio
async def test_update_env_file_write_error(tmp_path, mock_logger):
    env_content = "KEY1=value1\n"
    env_path = tmp_path / ".env"
    env_path.write_text(env_content) # Create the actual file for os.path.exists

    key = "KEY1"
    value = "new_value"

    with patch('os.path.exists', return_value=True):
        # Simulate an IOError when opening the file for writing
        # We need to mock the read part first, then the write part fails
        def mock_open_side_effect(file, mode):
            if mode == 'r':
                # Return a mock file handle for reading
                m = mock_open(read_data=env_content)
                return m.return_value
            elif mode == 'w':
                raise IOError("Permission denied")
            
        with patch('builtins.open', side_effect=mock_open_side_effect):
            result = await update_env_file(key, value)

            assert result is False
            mock_logger.error.assert_called_once()
            assert "No se pudo actualizar el archivo .env" in mock_logger.error.call_args[0][0]
