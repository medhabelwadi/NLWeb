/**
 * ManagedEventSource Class
 * Handles EventSource connections with retry logic and message processing
 */

export class ManagedEventSource {
  /**
   * Creates a new ManagedEventSource
   * 
   * @param {string} url - The URL to connect to
   * @param {Object} options - Options for the EventSource
   * @param {number} options.maxRetries - Maximum number of retries
   */
  constructor(url, options = {}) {
    this.url = url;
    this.options = options;
    this.maxRetries = options.maxRetries || 3;
    this.retryCount = 0;
    this.eventSource = null;
    this.isStopped = false;
    this.query_id = null;
  }

  /**
   * Connects to the EventSource
   * 
   * @param {Object} chatInterface - The chat interface instance
   */
  connect(chatInterface) {
    if (this.isStopped) {
      return;
    }
    
    this.eventSource = new EventSource(this.url);
    this.eventSource.chatInterface = chatInterface;
    
    this.eventSource.onopen = () => {
      this.retryCount = 0; // Reset retry count on successful connection
    };

    this.eventSource.onerror = (error) => {
      if (this.eventSource.readyState === EventSource.CLOSED) {
        console.log('Connection was closed');
        
        if (this.retryCount < this.maxRetries) {
          this.retryCount++;
          console.log(`Retry attempt ${this.retryCount} of ${this.maxRetries}`);
          
          // Implement exponential backoff
          const backoffTime = Math.min(1000 * Math.pow(2, this.retryCount), 10000);
          setTimeout(() => this.connect(), backoffTime);
        } else {
          console.log('Max retries reached, stopping reconnection attempts');
          this.stop();
        }
      }
    };

    this.eventSource.onmessage = this.handleMessage.bind(this);
  }

  /**
   * Handles incoming messages from the EventSource
   * 
   * @param {Event} event - The message event
   */
  handleMessage(event) {
    const chatInterface = this.eventSource.chatInterface;
    
    // Handle first message by removing loading dots
    if (chatInterface.dotsStillThere) {
      chatInterface.handleFirstMessage();
      
      // Setup new message container
      const messageDiv = document.createElement('div');
      messageDiv.className = 'message assistant-message';
      const bubble = document.createElement('div'); 
      bubble.className = 'message-bubble';
      messageDiv.appendChild(bubble);
      
      chatInterface.bubble = bubble;
      chatInterface.messagesArea.appendChild(messageDiv);
      chatInterface.currentItems = [];
      chatInterface.thisRoundRemembered = null;
    }
    
    // Parse the JSON data
    const data = JSON.parse(event.data);
    
    // Verify query_id matches
    if (this.query_id && data.query_id && this.query_id !== data.query_id) {
      console.log("Query ID mismatch, ignoring message");
      return;
    }
    
    // Process message based on type
    this.processMessageByType(data, chatInterface);
  }

  /**
   * Processes messages based on their type
   * 
   * @param {Object} data - The message data
   * @param {Object} chatInterface - The chat interface instance
   */
  processMessageByType(data, chatInterface) {
    const messageType = data.message_type;
    
    switch(messageType) {
      case "query_analysis":
        this.handleQueryAnalysis(data, chatInterface);
        break;
      case "remember":
        chatInterface.memoryMessage(data.message, chatInterface);
        break;
      case "asking_sites":
        chatInterface.sourcesMessage = chatInterface.createIntermediateMessageHtml(data.message);
        chatInterface.bubble.appendChild(chatInterface.sourcesMessage);
        break;
      case "site_is_irrelevant_to_query":
        chatInterface.siteIsIrrelevantToQuery(data.message, chatInterface);
        break;
      case "ask_user":
        chatInterface.askUserMessage(data.message, chatInterface);
        break;
      case "item_details":
        chatInterface.itemDetailsMessage(data.message, chatInterface);
        break;
      case "result_batch":
        this.handleResultBatch(data, chatInterface);
        break;
      case "intermediate_message":
        chatInterface.bubble.appendChild(chatInterface.createIntermediateMessageHtml(data.message));
        break;
      case "summary":
        chatInterface.thisRoundSummary = chatInterface.createIntermediateMessageHtml(data.message);
        chatInterface.resortResults();
        break;
      case "nlws":
        this.handleNLWS(data, chatInterface);
        break;
      case "complete":
        chatInterface.resortResults();
        chatInterface.scrollDiv.scrollIntoView();
        this.close();
        break;
    }
  }
  
  /**
   * Handles query analysis messages
   * 
   * @param {Object} data - The message data
   * @param {Object} chatInterface - The chat interface instance
   */
  handleQueryAnalysis(data, chatInterface) {
    chatInterface.itemToRemember.push(data.item_to_remember);
    chatInterface.decontextualizedQuery = data.decontextualized_query;
    chatInterface.possiblyAnnotateUserQuery(data.decontextualized_query);
    
    if (chatInterface.itemToRemember) {
      chatInterface.memoryMessage(data.item_to_remember, chatInterface);
    }
  }
  
  /**
   * Handles result batch messages
   * 
   * @param {Object} data - The message data
   * @param {Object} chatInterface - The chat interface instance
   */
  handleResultBatch(data, chatInterface) {
    for (const item of data.results) {
      const domItem = chatInterface.createJsonItemHtml(item);
      chatInterface.currentItems.push([item, domItem]);
      chatInterface.bubble.appendChild(domItem);
      chatInterface.num_results_sent++;
    }
    chatInterface.resortResults();
  }
  
  /**
   * Handles NLWS messages
   * 
   * @param {Object} data - The message data
   * @param {Object} chatInterface - The chat interface instance
   */
  handleNLWS(data, chatInterface) {
    // Clear existing content
    while (chatInterface.bubble.firstChild) {
      chatInterface.bubble.removeChild(chatInterface.bubble.firstChild);
    }
    
    chatInterface.itemDetailsMessage(data.answer, chatInterface);
    
    for (const item of data.items) {
      const domItem = chatInterface.createJsonItemHtml(item);
      chatInterface.currentItems.push([item, domItem]);
      chatInterface.bubble.appendChild(domItem);
    }
  }

  /**
   * Stops the EventSource connection
   */
  stop() {
    this.isStopped = true;
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * Closes the EventSource connection
   */
  close() {
    this.stop();
  }

  /**
   * Resets and reconnects the EventSource
   */
  reset() {
    this.retryCount = 0;
    this.isStopped = false;
    this.stop();
    this.connect();
  }
}