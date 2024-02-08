from services.chat_repo.chat_repo_memory import ChatRepoMemory

from tests.unit.chat_repo.chat_repo_test_base import ChatRepoTestBase, ChatRepo


class TestChatRepoMemory(ChatRepoTestBase):
    repo: ChatRepo
    repo_class: type = ChatRepoMemory
