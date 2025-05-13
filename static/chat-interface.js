/**
 * ChatInterface Class
 * Handles the UI and message processing for the chat interface
 */

import { ManagedEventSource } from './managed-event-source.js';
import { JsonRenderer, TypeRendererFactory, jsonLdToHtml, escapeHtml } from './utils.js';
import { RecipeRenderer } from './recipe-renderer.js'; 

export class ChatInterface {
  /**
   * Creates a new ChatInterface
   * 
   * @param {string} site - The site to use for search
   * @param {string} display_mode - The display mode
   * @param {string} generate_mode - The generate mode
   * @param {boolean} appendElements - Whether to append interface elements immediately
   */
  constructor(site = null, display_mode = "dropdown", generate_mode = "list", appendElements = true) {
    // Initialize properties
    this.site = site;
    this.display_mode = display_mode;
    this.generate_mode = generate_mode;
    this.eventSource = null;
    this.dotsStillThere = false;
    this.debug_mode = false;
    
    // Create JSON renderer
    this.jsonRenderer = new JsonRenderer();
    TypeRendererFactory.registerAll(this.jsonRenderer);
    TypeRendererFactory.registerRenderer(RecipeRenderer, this.jsonRenderer);
  
    // Parse URL parameters
    this.parseUrlParams();
    
    // Create UI elements but don't append yet if appendElements is false
    this.createInterface(display_mode, appendElements);
    this.bindEvents();
    
    // Reset state
    this.resetChatState();
    
    // Process initial query if provided in URL
    if (this.initialQuery) {
      this.sendMessage(decodeURIComponent(this.initialQuery));
    }
  }

  /**
   * Parses URL parameters for configuration
   */
  parseUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    this.initialQuery = urlParams.get('query');
    const prevMessagesStr = urlParams.get('prev');
    const contextUrl = urlParams.get('context_url');
    const urlGenerateMode = urlParams.get('generate_mode');
    
    if (urlGenerateMode) {
      this.generate_mode = urlGenerateMode;
    }
    
    try {
      this.prevMessages = prevMessagesStr ? JSON.parse(decodeURIComponent(prevMessagesStr)) : [];
    } catch (e) {
      console.error('Error parsing previous messages:', e);
      this.prevMessages = [];
    }
  }

  /**
   * Resets the chat state
   */
  resetChatState() {
    if (this.messagesArea) {
      this.messagesArea.innerHTML = '';
    }
    this.messages = [];
    this.prevMessages =  [];
    this.currentMessage = [];
    this.currentItems = [];
    this.itemToRemember = [];
    this.thisRoundSummary = null;
    this.num_results_sent = 0;
  }

  /**
   * Creates the interface elements
   * 
   * @param {string} display_mode - The display mode
   * @param {boolean} appendElements - Whether to append elements immediately
   */
  createInterface(display_mode = "dropdown", appendElements = true) {
    // Get main container reference but don't append to it yet
    this.container = document.getElementById('chat-container');
    
    // Create messages area
    this.messagesArea = document.createElement('div');
    this.messagesArea.className = (display_mode === "dropdown" ? 'messages' : 'messages_full');
    
    // Create input area
    this.inputArea = document.createElement('div');
    this.inputArea.className = (display_mode === "dropdown" ? 'input-area' : 'input-area_full');

    // Create input field
    this.input = document.createElement('textarea');
    this.input.className = 'message-input';
    this.input.placeholder = 'Type your message...';
    this.input.style.minHeight = '60px'; // Set minimum height
    this.input.style.height = '60px'; // Initial height
    this.input.rows = 1; // Start with one row
    this.input.style.resize = 'none'; // Prevent manual resizing
    this.input.style.overflow = 'hidden'; // Hide scrollbar

    // Create send button
    this.sendButton = document.createElement('button');
    this.sendButton.className = 'send-button';
    this.sendButton.textContent = 'Send';

    // Assemble the input area
    this.inputArea.appendChild(this.input);
    this.inputArea.appendChild(this.sendButton);
    
    // Append to container if requested
    if (appendElements) {
      this.appendInterfaceElements(this.container);
    }
  }
  
  /**
   * Appends the interface elements to the specified container
   * 
   * @param {HTMLElement} container - The container to append to
   */
  appendInterfaceElements(container) {
    container.appendChild(this.messagesArea);
    container.appendChild(this.inputArea);
  }

  /**
   * Binds event handlers to UI elements
   */
  bindEvents() {
    // Send message on button click
    this.sendButton.addEventListener('click', () => this.sendMessage());

    // Send message on Enter (but allow Shift+Enter for new lines)
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });
    
    // Auto-resize textarea based on content
    this.input.addEventListener('input', () => {
      // Reset height to auto first to correctly calculate new height
      this.input.style.height = 'auto';
      
      // Set new height based on scrollHeight, with a minimum height
      const newHeight = Math.max(60, Math.min(this.input.scrollHeight, 150));
      this.input.style.height = newHeight + 'px';
    });
  }

  /**
   * Sends a message
   * 
   * @param {string} query - The message to send
   */
  sendMessage(query = null) {
    const message = query || this.input.value.trim();
    if (!message) return;

    // Add user message
    this.addMessage(message, 'user');
    this.currentMessage = message;
    this.input.value = '';
    
    // Reset input field height
    this.input.style.height = '60px';

    // Get response
    this.getResponse(message);
  }

  /**
   * Adds a message to the chat
   * 
   * @param {string} content - The message content
   * @param {string} sender - The sender (user or assistant)
   */
  addMessage(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    if (sender === "user") {
      this.lastUserMessageDiv = messageDiv;
      const scrollDiv = document.createElement('span');
      scrollDiv.id = this.quickHash(content.toString());
      messageDiv.appendChild(scrollDiv);
      messageDiv.appendChild(document.createElement('br'));
      messageDiv.appendChild(document.createElement('br'));
      this.scrollDiv = scrollDiv;
    }
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    let parsedContent;
    try {
      parsedContent = JSON.parse(content);
    } catch (e) {
      parsedContent = content;
    }
    
    if (Array.isArray(parsedContent)) {
      // Safer approach: Create DOM elements instead of using innerHTML
      parsedContent.forEach(obj => {
        const itemElement = this.createJsonItemHtml(obj);
        bubble.appendChild(itemElement);
        
        // Add line breaks between items
        if (parsedContent.indexOf(obj) < parsedContent.length - 1) {
          bubble.appendChild(document.createElement('br'));
          bubble.appendChild(document.createElement('br'));
        }
      });
    } else {
      // Use textContent for regular messages to prevent XSS
      bubble.textContent = content;
    }

    messageDiv.appendChild(bubble);
    this.messagesArea.appendChild(messageDiv);
    
    // Scroll to the bottom to show the new message
    this.scrollToBottom();

    this.messages.push({ content, sender });
    this.currentMessage = "";
  }
  
  /**
   * Scrolls the message area to the bottom
   */
  scrollToBottom() {
    this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
  }

  /**
   * Gets a response for the user's message
   * 
   * @param {string} message - The user's message
   */
  async getResponse(message) {
    // Add loading state
    const loadingDots = '...';
    this.addMessage(loadingDots, 'assistant');
    this.dotsStillThere = true;
 
    try {
      console.log("generate_mode", this.generate_mode);
      const selectedSite = (this.site || (this.siteSelect && this.siteSelect.value));
      const selectedDatabase = this.database || (this.dbSelect && this.dbSelect.value) || 'azure_ai_search_1';
      const prev = JSON.stringify(this.prevMessages);
      const generate_mode = this.generate_mode;
      const context_url = this.context_url && this.context_url.value ? this.context_url.value : '';
      
      // Generate a unique query ID
      const timestamp = new Date().getTime();
      const queryId = `query_${timestamp}_${Math.floor(Math.random() * 1000)}`;
      console.log("Generated query ID:", queryId);
      
      // Build query parameters
      const queryParams = new URLSearchParams();
      queryParams.append('query_id', queryId);
      queryParams.append('query', message);
      queryParams.append('site', selectedSite);
      queryParams.append('db', selectedDatabase);
      queryParams.append('generate_mode', generate_mode);
      queryParams.append('prev', prev);
      queryParams.append('item_to_remember', this.itemToRemember || '');
      queryParams.append('context_url', context_url);
      
      const queryString = queryParams.toString();
      const url = `/ask?${queryString}`;
      console.log("url", url);
      
      this.eventSource = new ManagedEventSource(url);
      this.eventSource.query_id = queryId;
      this.eventSource.connect(this);
      this.prevMessages.push(message);
    } catch (error) {
      console.error('Error fetching response:', error);
    }
  }
  

  /**
   * Handles the first message by removing loading dots
   */
  handleFirstMessage() {
    this.dotsStillThere = false;
    this.messagesArea.removeChild(this.messagesArea.lastChild);
  }

  /**
   * Creates HTML for a JSON item
   * 
   * @param {Object} item - The item data
   * @returns {HTMLElement} - The HTML element
   */
  createJsonItemHtml(item) {
    return this.jsonRenderer.createJsonItemHtml(item);
  }

  /**
   * Gets the name of an item
   * 
   * @param {Object} item - The item data
   * @returns {string} - The item name
   */
  getItemName(item) {
    return this.jsonRenderer.getItemName(item);
  }

  /**
   * Generates a quick hash for a string
   * 
   * @param {string} string - The string to hash
   * @returns {number} - The hash value
   */
  quickHash(string) {
    let hash = 0;
    for (let i = 0; i < string.length; i++) {
      const char = string.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash |= 0; // Convert to 32-bit integer
    }
    return hash;
  }

  /**
   * Creates an HTML element for an intermediate message
   * 
   * @param {string} message - The message
   * @returns {HTMLElement} - The HTML element
   */
  createIntermediateMessageHtml(message) {
    const container = document.createElement('div');
    container.className = 'intermediate-container';
    // Use textContent for safe insertion
    container.textContent = message || '';
    return container;
  }

  /**
   * Displays a memory message
   * 
   * @param {string} itemToRemember - The item to remember
   * @param {Object} chatInterface - The chat interface instance
   * @returns {HTMLElement} - The message element
   */
  memoryMessage(itemToRemember, chatInterface) { 
    if (itemToRemember) {
      const messageDiv = document.createElement('div');
      messageDiv.className = 'remember-message';
      // Use textContent for safe insertion
      messageDiv.textContent = itemToRemember;
      chatInterface.thisRoundRemembered = messageDiv;
      chatInterface.bubble.appendChild(messageDiv);
      return messageDiv;
    }
  }

  /**
   * Displays an ask user message
   * 
   * @param {string} message - The message
   * @param {Object} chatInterface - The chat interface instance
   */
  askUserMessage(message, chatInterface) { 
    console.log("askUserMessage", message);
    const messageDiv = document.createElement('div');
    messageDiv.className = 'ask-user-message';
    // Use textContent for safe insertion
    messageDiv.textContent = message || '';
    chatInterface.bubble.appendChild(messageDiv);
  }

  /**
   * Displays a site is irrelevant to query message
   * 
   * @param {string} message - The message
   * @param {Object} chatInterface - The chat interface instance
   */
  siteIsIrrelevantToQuery(message, chatInterface) { 
    console.log("siteIsIrrelevantToQuery", message);
    const messageDiv = document.createElement('div');
    messageDiv.className = 'site-is-irrelevant-to-query';
    // Use textContent for safe insertion
    messageDiv.textContent = message || '';
    chatInterface.bubble.appendChild(messageDiv);
  }

  /**
   * Displays an item details message
   * 
   * @param {string} itemDetails - The item details
   * @param {Object} chatInterface - The chat interface instance
   * @returns {HTMLElement} - The message element
   */
  itemDetailsMessage(itemDetails, chatInterface) { 
    if (itemDetails) {
      const messageDiv = document.createElement('div');
      messageDiv.className = 'item-details-message';
      // Use textContent for safe insertion
      messageDiv.textContent = itemDetails;
      chatInterface.thisRoundRemembered = messageDiv;
      chatInterface.bubble.appendChild(messageDiv);
      return messageDiv;
    }
  }

  /**
   * Annotates the user query with decontextualized query
   * 
   * @param {string} decontextualizedQuery - The decontextualized query
   */
  possiblyAnnotateUserQuery(decontextualizedQuery) {
    const msgDiv = this.lastUserMessageDiv;
    if (msgDiv && decontextualizedQuery) {
      // Optional: Uncomment to show decontextualized query
      // Use a safer approach if uncommenting
      // const originalContent = this.currentMessage;
      // msgDiv.textContent = '';
      // 
      // const textNode = document.createTextNode(originalContent);
      // msgDiv.appendChild(textNode);
      // msgDiv.appendChild(document.createElement('br'));
      // 
      // const decontextSpan = document.createElement('span');
      // decontextSpan.className = 'decontextualized-query';
      // decontextSpan.textContent = decontextualizedQuery;
      // msgDiv.appendChild(decontextSpan);
    }
  }
  
  /**
   * Resorts the results by score
   */
  resortResults() {
    if (this.currentItems.length > 0) {
      // Sort by score in descending order
      this.currentItems.sort((a, b) => b[0].score - a[0].score);
      
      // Clear existing children
      while (this.bubble.firstChild) {
        this.bubble.removeChild(this.bubble.firstChild);
      }
      
      // Add sorted content back in proper order
      if (this.thisRoundRemembered) {
        this.bubble.appendChild(this.thisRoundRemembered);
      }
      
      if (this.sourcesMessage) {
        this.bubble.appendChild(this.sourcesMessage);
      }
      
      if (this.thisRoundSummary) {
        this.bubble.appendChild(this.thisRoundSummary);
      }
      
      // Add sorted result items
      for (const [item, domItem] of this.currentItems) {
        this.bubble.appendChild(domItem);
      }
    }
  }

  /**
   * Creates HTML for insufficient results message
   * 
   * @returns {HTMLElement} - The HTML element
   */
  createInsufficientResultsHtml() {
    const container = document.createElement('div');
    container.className = 'intermediate-container';
    container.appendChild(document.createElement('br'));
    
    if (this.currentItems.length > 0) {
      container.textContent = "I couldn't find any more results that are relevant to your query.";
    } else {
      container.textContent = "I couldn't find any results that are relevant to your query.";
    }
    
    container.appendChild(document.createElement('br'));
    return container;
  }

  /**
   * Creates a debug string for the current items
   * 
   * @returns {string} - The debug string
   */
  createDebugString() {
    return jsonLdToHtml(this.currentItems);
  }
  
  /**
   * Sanitizes a URL to prevent javascript: protocol and other potentially dangerous URLs
   * 
   * @param {string} url - The URL to sanitize
   * @returns {string} - The sanitized URL
   */
  sanitizeUrl(url) {
    if (!url || typeof url !== 'string') return '#';
    
    // Remove leading and trailing whitespace
    const trimmedUrl = url.trim();
    
    // Check for javascript: protocol or other dangerous protocols
    const protocolPattern = /^(javascript|data|vbscript|file):/i;
    if (protocolPattern.test(trimmedUrl)) {
      return '#';
    }
    
    return trimmedUrl;
  }
}