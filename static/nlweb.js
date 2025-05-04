/**
 * Main entry file for the streaming chat application
 * Imports and initializes all components
 */

// Import modules
import { applyStyles } from './styles.js';
import { ManagedEventSource } from './managed-event-source.js';
import { ChatInterface } from './chat-interface.js';

// Initialize styles
applyStyles();

// Make ChatInterface available globally
window.ChatInterface = ChatInterface;
window.ManagedEventSource = ManagedEventSource;

// Initialize the chat interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // You can add initialization code here if needed
  console.log('Chat interface ready');
});