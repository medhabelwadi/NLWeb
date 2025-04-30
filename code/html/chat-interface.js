/**
 * ChatInterface Class
 * Handles the UI and message processing for the chat interface
 */

import { ManagedEventSource } from './managed-event-source.js';
import { jsonLdToHtml } from './utils.js';


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
    
    this.prevMessages = prevMessagesStr ? JSON.parse(decodeURIComponent(prevMessagesStr)) : [];
  }

  /**
   * Resets the chat state
   */
  resetChatState() {
    if (this.messagesArea) {
      this.messagesArea.innerHTML = '';
    }
    this.messages = [];
    this.prevMessages = this.prevMessages || [];
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
      bubble.innerHTML = parsedContent.map(obj => {
        return this.createJsonItemHtml(obj).outerHTML;
      }).join('<br><br>');
    } else {
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
    const container = document.createElement('div');
    container.className = 'item-container';

    // Left content div (title + description)
    const contentDiv = document.createElement('div');
    contentDiv.className = 'item-content';

    // Title row with link and info icon
    this.createTitleRow(item, contentDiv);

    // Description
    const description = document.createElement('div');
    description.textContent = item.description;
    description.className = 'item-description';
    contentDiv.appendChild(description);

    // For NL web search display mode
    if (this.display_mode === "nlwebsearch") {
      this.addVisibleUrl(item, contentDiv);
    }
    
    // Add type-specific content
    this.typeSpecificContent(item, contentDiv);

    container.appendChild(contentDiv);

    // Add image if available
    this.addImageIfAvailable(item, container);

    return container;
  }
  
  /**
   * Creates a title row for an item
   * 
   * @param {Object} item - The item data
   * @param {HTMLElement} contentDiv - The content div
   */
  createTitleRow(item, contentDiv) {
    const titleRow = document.createElement('div');
    titleRow.className = 'item-title-row';

    // Title/link
    const titleLink = document.createElement('a');
    titleLink.href = item.url;
    const itemName = this.getItemName(item);
    titleLink.textContent = this.htmlUnescape(itemName);
    titleLink.className = 'item-title-link';
    titleRow.appendChild(titleLink);

    // Info icon
    const infoIcon = document.createElement('span');
    infoIcon.innerHTML = '<img src="images/info.png">';
    infoIcon.className = 'item-info-icon';
    infoIcon.title = item.explanation + "(score=" + item.score + ")" + "(Ranking time=" + item.time + ")";
    titleRow.appendChild(infoIcon);

    contentDiv.appendChild(titleRow);
  }
  
  /**
   * Adds a visible URL to the content div
   * 
   * @param {Object} item - The item data
   * @param {HTMLElement} contentDiv - The content div
   */
  addVisibleUrl(item, contentDiv) {
    const visibleUrlLink = document.createElement("a");
    visibleUrlLink.href = item.siteUrl;
    visibleUrlLink.textContent = item.site;
    visibleUrlLink.className = 'item-site-link';
    contentDiv.appendChild(visibleUrlLink);
  }
  
  /**
   * Adds an image to the item if available
   * 
   * @param {Object} item - The item data
   * @param {HTMLElement} container - The container element
   */
  addImageIfAvailable(item, container) {
    if (item.schema_object) {
      const imgURL = this.extractImage(item.schema_object);
      if (imgURL) {
        const imageDiv = document.createElement('div');
        const img = document.createElement('img');
        img.src = imgURL;
        img.className = 'item-image';
        imageDiv.appendChild(img);
        container.appendChild(imageDiv);
      }
    }
  }
  
  /**
   * Gets the name of an item
   * 
   * @param {Object} item - The item data
   * @returns {string} - The item name
   */
  getItemName(item) {
    if (item.name) {
      return item.name;
    } else if (item.schema_object && item.schema_object.keywords) {
      return item.schema_object.keywords;
    }
    return item.url;
  }
  
  /**
   * Adds type-specific content to the item
   * 
   * @param {Object} item - The item data
   * @param {HTMLElement} contentDiv - The content div
   */
  typeSpecificContent(item, contentDiv) {
    if (!item.schema_object) {
      return;
    }
    
    const objType = item.schema_object['@type'];
    const houseTypes = ["SingleFamilyResidence", "Apartment", "Townhouse", "House", "Condominium", "RealEstateListing"];
    
    if (objType === "PodcastEpisode") {
      this.possiblyAddExplanation(item, contentDiv, true);
      return;
    }
    
    if (houseTypes.includes(objType)) {
      this.addRealEstateDetails(item, contentDiv);
    }
  }
  
  /**
   * Adds real estate details to an item
   * 
   * @param {Object} item - The item data
   * @param {HTMLElement} contentDiv - The content div
   */
  addRealEstateDetails(item, contentDiv) {
    const detailsDiv = this.possiblyAddExplanation(item, contentDiv, true);
    detailsDiv.className = 'item-real-estate-details';
    
    const schema = item.schema_object;
    const price = schema.price;
    const address = schema.address;
    const numBedrooms = schema.numberOfRooms;
    const numBathrooms = schema.numberOfBathroomsTotal;
    const sqft = schema.floorSize?.value;
    
    let priceValue = price;
    if (typeof price === 'object') {
      priceValue = price.price || price.value || price;
      priceValue = Math.round(priceValue / 100000) * 100000;
      priceValue = priceValue.toLocaleString('en-US');
    }

    detailsDiv.appendChild(this.makeAsSpan(address.streetAddress + ", " + address.addressLocality));
    detailsDiv.appendChild(document.createElement('br'));
    detailsDiv.appendChild(this.makeAsSpan(`${numBedrooms} bedrooms, ${numBathrooms} bathrooms, ${sqft} sqft`));
    detailsDiv.appendChild(document.createElement('br'));
    
    if (priceValue) {
      detailsDiv.appendChild(this.makeAsSpan(`Listed at ${priceValue}`));
    }
  }
  
  /**
   * Creates a span element with the given content
   * 
   * @param {string} content - The content for the span
   * @returns {HTMLElement} - The span element
   */
  makeAsSpan(content) {
    const span = document.createElement('span');
    span.textContent = content;
    span.className = 'item-details-text';
    return span;
  }

  /**
   * Adds an explanation to an item
   * 
   * @param {Object} item - The item data
   * @param {HTMLElement} contentDiv - The content div
   * @param {boolean} force - Whether to force adding the explanation
   * @returns {HTMLElement} - The details div
   */
  possiblyAddExplanation(item, contentDiv, force = false) {
    const detailsDiv = document.createElement('div'); 
    contentDiv.appendChild(document.createElement('br'));
    const explSpan = this.makeAsSpan(item.explanation);
    explSpan.className = 'item-explanation';
    detailsDiv.appendChild(explSpan);
    contentDiv.appendChild(detailsDiv);
    return detailsDiv;
  }

  /**
   * Extracts an image URL from a schema object
   * 
   * @param {Object} schema_object - The schema object
   * @returns {string|null} - The image URL or null
   */
  extractImage(schema_object) {
    if (schema_object && schema_object.image) {
      return this.extractImageInternal(schema_object.image);
    }
    return null;
  }

  /**
   * Extracts an image URL from various image formats
   * 
   * @param {*} image - The image data
   * @returns {string|null} - The image URL or null
   */
  extractImageInternal(image) {
    if (typeof image === 'string') {
      return image;
    } else if (typeof image === 'object' && image.url) {
      return image.url;
    } else if (typeof image === 'object' && image.contentUrl) {
      return image.contentUrl;
    } else if (image instanceof Array) {
      if (image[0] && typeof image[0] === 'string') {
        return image[0];
      } else if (image[0] && typeof image[0] === 'object') {
        return this.extractImageInternal(image[0]);
      }
    } 
    return null;
  }

  /**
   * Unescapes HTML entities in a string
   * 
   * @param {string} str - The string to unescape
   * @returns {string} - The unescaped string
   */
  htmlUnescape(str) {
    const div = document.createElement("div");
    div.innerHTML = str;
    return div.textContent || div.innerText;
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
    container.textContent = message;
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
    messageDiv.textContent = message;
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
    messageDiv.textContent = message;
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
    if (msgDiv) {
      // Optional: Uncomment to show decontextualized query
      // msgDiv.innerHTML = this.currentMessage + "<br><span class=\"decontextualized-query\">" + decontextualizedQuery + "</span>";
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
}