/**
 * DropdownInterface Class
 * Handles the dropdown UI elements for site selection and options
 */

export class DropdownInterface {
  /**
   * Creates a new DropdownInterface
   * 
   * @param {Object} chatInterface - The main chat interface instance
   * @param {HTMLElement} container - The container element to append to
   */
  constructor(chatInterface, container) {
    this.chatInterface = chatInterface;
    this.container = container;
    
    // Create the dropdown interface
    this.createSelectors();
  }

  /**
   * Creates selector controls
   */
  createSelectors() {
    // Create selectors container
    const selector = document.createElement('div');
    this.selector = selector;
    selector.className = 'site-selector';

    // Create site selector
    this.createSiteSelector();
    
    // Create generate mode selector
    this.createGenerateModeSelector();
    
    // Create database selector if enabled
    if (this.chatInterface.enableDatabaseSelector) {
      this.createDatabaseSelector();
    }
     
    // Create clear chat icon
    this.addClearChatIcon();

    // Create debug icon
    this.addDebugIcon();

    // Create context URL input
    this.addContextUrlInput();

    // Add to container - this will place it at the top of the container
    this.container.prepend(this.selector);
  }
  
  /**
   * Creates the site selector dropdown
   */
  createSiteSelector() {
    const siteSelect = document.createElement('select');
    this.siteSelect = siteSelect;
    
    this.getSites().forEach(site => {
      const option = document.createElement('option');
      option.value = site;
      option.textContent = site;
      siteSelect.appendChild(option);
    });
    
    this.selector.appendChild(this.makeSelectorLabel("Site"));
    this.selector.appendChild(siteSelect);
    
    siteSelect.addEventListener('change', () => {
      this.chatInterface.site = siteSelect.value;
      this.chatInterface.resetChatState();
    });
    
    // Set initial value if chatInterface has a site
    if (this.chatInterface.site) {
      siteSelect.value = this.chatInterface.site;
    }
    
    // Make siteSelect accessible to chatInterface
    this.chatInterface.siteSelect = siteSelect;
  }
  
  /**
   * Creates the generate mode selector dropdown
   */
  createGenerateModeSelector() {
    const generateModeSelect = document.createElement('select');
    this.generateModeSelect = generateModeSelect;
    
    this.getGenerateModes().forEach(mode => {
      const option = document.createElement('option');
      option.value = mode;
      option.textContent = mode;
      generateModeSelect.appendChild(option);
    });
    
    this.selector.appendChild(this.makeSelectorLabel("Mode"));
    this.selector.appendChild(generateModeSelect);
    
    generateModeSelect.addEventListener('change', () => {
      this.chatInterface.generate_mode = generateModeSelect.value;
      this.chatInterface.resetChatState();
    });
    
    // Set initial value
    generateModeSelect.value = this.chatInterface.generate_mode;
    
    // Make generateModeSelect accessible to chatInterface
    this.chatInterface.generateModeSelect = generateModeSelect;
  }
  
  /**
   * Creates the database selector dropdown
   */
  createDatabaseSelector() {
    const dbSelect = document.createElement('select');
    this.dbSelect = dbSelect;
    
    this.getDatabases().forEach(db => {
      const option = document.createElement('option');
      option.value = db.id;
      option.textContent = db.name;
      dbSelect.appendChild(option);
    });
    
    this.selector.appendChild(this.makeSelectorLabel("Database"));
    this.selector.appendChild(dbSelect);
    
    dbSelect.addEventListener('change', () => {
      this.chatInterface.database = dbSelect.value;
      this.chatInterface.resetChatState();
    });
    
    // Set initial value to preferred endpoint from config
    dbSelect.value = "azure_ai_search_1";
    this.chatInterface.database = "azure_ai_search_1";
    
    // Make dbSelect accessible to chatInterface
    this.chatInterface.dbSelect = dbSelect;
  }
  
  /**
   * Adds the clear chat icon
   */
  addClearChatIcon() {
    const clearIcon = document.createElement('span');
    clearIcon.innerHTML = '<img src="images/clear.jpeg" class="selector-icon">';
    clearIcon.title = "Clear chat history";
    clearIcon.addEventListener('click', () => {
      this.chatInterface.resetChatState();
    });
    this.selector.appendChild(clearIcon);
  }
  
  /**
   * Adds the debug icon
   */
  addDebugIcon() {
    const debugIcon = document.createElement('span');
    debugIcon.innerHTML = '<img src="images/debug.png" class="selector-icon">';
    debugIcon.title = "Debug";
    debugIcon.addEventListener('click', () => {
      if (this.chatInterface.debug_mode) {
        this.chatInterface.debug_mode = false;
        this.chatInterface.bubble.innerHTML = '';
        this.chatInterface.resortResults();
      } else {
        this.chatInterface.debug_mode = true;
        this.chatInterface.bubble.innerHTML = this.chatInterface.createDebugString();
      }
    });
    this.selector.appendChild(debugIcon);
  }
  
  /**
   * Adds the context URL input
   */
  addContextUrlInput() {
    const contextUrlDiv = document.createElement('div');
    contextUrlDiv.id = 'context_url_div';
    contextUrlDiv.className = 'context-url-container';
        
    const contextUrlInput = document.createElement('input');
    contextUrlInput.type = 'text';
    contextUrlInput.id = 'context_url';
    contextUrlInput.placeholder = 'Enter Context URL';
    contextUrlInput.className = 'context-url-input';
        
    contextUrlDiv.appendChild(this.makeSelectorLabel("Context URL"));
    contextUrlDiv.appendChild(contextUrlInput);
    this.selector.appendChild(contextUrlDiv);
    
    // Make context_url accessible to chatInterface
    this.chatInterface.context_url = contextUrlInput;
  }
  
  /**
   * Makes a label for selectors
   * 
   * @param {string} label - The label text
   * @returns {HTMLElement} - The label element
   */
  makeSelectorLabel(label) {
    const labelDiv = document.createElement('span');
    labelDiv.textContent = label;
    labelDiv.className = 'selector-label';
    return labelDiv;
  }

  /**
   * Gets the available sites for the selector
   * 
   * @returns {Array} - Array of site names
   */
  getSites() {
    return [
      'imdb', 'nytimes', 'alltrails', 'allbirds', 'seriouseats', 'oreilly',
      'npr podcasts', 'backcountry', 'bc_product', 'neurips', 'zillow', 'eventbrite',
      'tripadvisor', 'woksoflife', 'cheftariq', 'hebbarskitchen',  'scifi_movies',
      'latam_recipes', 'spruce', 'med podcast', 'allbirdsdd', 'all'
    ];
  }

  /**
   * Gets the available generate modes for the selector
   * 
   * @returns {Array} - Array of generate mode names
   */
  getGenerateModes() {
    return ['list', 'summarize', 'generate'];
  }
  
  /**
   * Gets the available databases for the selector
   * 
   * @returns {Array} - Array of database configurations
   */
  getDatabases() {
    return [
      { id: 'azure_ai_search_1', name: 'NLWeb_Crawl' },
      { id: 'azure_ai_search_2', name: 'Bing_Crawl' },
      { id: 'milvus_1', name: 'Milvus' }
    ];
  }
}
