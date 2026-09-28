export interface User {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  created_at: string;
}

export interface AuthenticationResponse {
  user: User;
  csrf_token: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  token_count: number | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation { messages: ChatMessage[]; }

export interface ChatResponse {
  conversation: Conversation;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  provider: string;
  model: string;
}
