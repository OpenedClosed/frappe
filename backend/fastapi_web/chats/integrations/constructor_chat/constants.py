"""Константы интеграции."""

CREATE_CHAT = """
mutation createApiChat($assistantId: ID!, $name: String, $messages: [MessageInput!]) {
  createApiChat(assistantId: $assistantId, name: $name, messages: $messages) { id }
}
"""

CREATE_MESSAGES = """
mutation createMessages($chatId: ID!, $messages: [MessageInput!]!) {
  createMessages(chatId: $chatId, messages: $messages)
}
"""

IMPORT_CHAT_MESSAGES = """
mutation CreateChatMessages(
  $assistantId: String!,
  $chatTitle: String,
  $externalChatId: String!,
  $messages: [MessageInput!]!
) {
  createChatMessages(
    assistantId: $assistantId,
    chatTitle: $chatTitle,
    externalChatId: $externalChatId,
    messages: $messages
  ) { id createdAt name type }
}
"""
