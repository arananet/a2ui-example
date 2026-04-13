/**
 * A2UI Photo Explorer — Visual Frontend JavaScript
 *
 * Handles:
 *  - A2A agent communication via /api/chat proxy
 *  - Rendering A2UI component trees (beginRendering, surfaceUpdate, dataModelUpdate)
 *  - Dynamic theming based on agent-specified primaryColor
 *  - Photo gallery rendering from valueStruct data model
 *  - Pagination via sendMessage pattern
 *  - A2UI payload inspector
 */

'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  sessionId: crypto.randomUUID(),
  isLoading: false,
  prevPagePrompt: null,
  nextPagePrompt: null,
  theme: { primaryColor: '#1565C0', font: 'Inter' },
};

// ---------------------------------------------------------------------------
// DOM References
// ---------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);

const dom = {
  chatMessages:    $('chatMessages'),
  chatForm:        $('chatForm'),
  chatInput:       $('chatInput'),
  sendBtn:         $('sendBtn'),
  suggestionChips: $('suggestionChips'),
  loadingOverlay:  $('loadingOverlay'),
  agentStatus:     $('agentStatus'),

  galleryEmpty:    $('galleryEmpty'),
  galleryContent:  $('galleryContent'),
  galleryQuery:    $('galleryQuery'),
  statTotal:       $('statTotal'),
  statPage:        $('statPage'),
  photoGrid:       $('photoGrid'),
  paginationRow:   $('paginationRow'),
  prevPageBtn:     $('prevPageBtn'),
  nextPageBtn:     $('nextPageBtn'),

  inspectorPanel:  $('inspectorPanel'),
  inspectorToggle: $('inspectorToggle'),
  inspectorBody:   $('inspectorBody'),
  inspectorChevron:$('inspectorChevron'),
  rawJson:         $('rawJson'),
  themeJson:       $('themeJson'),
  dataJson:        $('dataJson'),

  photoCardTemplate: $('photoCardTemplate'),
};

// ---------------------------------------------------------------------------
// Theme Management
// ---------------------------------------------------------------------------

/**
 * Applies a primary color from the A2UI beginRendering message to the page
 * by updating CSS custom properties.
 *
 * @param {string} hexColor - Hex color string, e.g. "#00897B"
 */
function applyTheme(hexColor) {
  const root = document.documentElement;
  root.style.setProperty('--color-primary', hexColor);

  // Derive dark variant (30% darkened via simple brightness shift)
  root.style.setProperty('--color-primary-dark', shadeColor(hexColor, -20));
  root.style.setProperty('--color-primary-glow', hexToRgba(hexColor, 0.25));

  // Update logo icon glow
  const logoIcon = document.querySelector('.logo-icon');
  if (logoIcon) {
    logoIcon.style.filter = `drop-shadow(0 0 8px ${hexColor})`;
  }
}

function shadeColor(hex, percent) {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.min(255, Math.max(0, (num >> 16) + percent));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + percent));
  const b = Math.min(255, Math.max(0, (num & 0xff) + percent));
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
}

function hexToRgba(hex, alpha) {
  const num = parseInt(hex.replace('#', ''), 16);
  return `rgba(${num >> 16}, ${(num >> 8) & 0xff}, ${num & 0xff}, ${alpha})`;
}

// ---------------------------------------------------------------------------
// Chat UI
// ---------------------------------------------------------------------------

/**
 * Appends a chat bubble to the message list.
 *
 * @param {string} text    - Message text content.
 * @param {'user'|'agent'|'error'} role - Visual style variant.
 * @param {boolean} hasA2ui - Whether the agent response included A2UI payload.
 */
function addChatBubble(text, role, hasA2ui = false) {
  const welcome = dom.chatMessages.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text || '(Agent processed your request.)';

  if (role === 'agent' && hasA2ui) {
    const tag = document.createElement('div');
    tag.className = 'a2ui-tag';
    tag.innerHTML = '⬡ A2UI rendered';
    bubble.appendChild(tag);
  }

  dom.chatMessages.appendChild(bubble);
  dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

// ---------------------------------------------------------------------------
// Photo Gallery Rendering
// ---------------------------------------------------------------------------

/**
 * Renders the full photo gallery from parsed A2UI photos data.
 *
 * @param {object} photos - valueStruct /photos data model.
 * @param {object} theme  - { primaryColor, font } from beginRendering.
 */
function renderGallery(photos, theme) {
  if (!photos || !photos.results || photos.results.length === 0) return;

  // Apply A2UI theme
  applyTheme(theme.primaryColor || '#1565C0');

  // Show gallery, hide empty state
  dom.galleryEmpty.style.display = 'none';
  dom.galleryContent.style.display = 'flex';
  dom.galleryContent.style.flexDirection = 'column';

  // Header
  dom.galleryQuery.textContent = `"${photos.query || ''}"`;
  dom.statTotal.textContent = photos.totalLabel || `${photos.total} photos`;
  dom.statPage.textContent = photos.pageLabel || `Page ${photos.currentPage}`;

  // Save pagination prompts
  state.prevPagePrompt = photos.prevPagePrompt || null;
  state.nextPagePrompt = photos.nextPagePrompt || null;

  // Render photo cards
  dom.photoGrid.innerHTML = '';
  photos.results.forEach((photo, index) => {
    const card = renderPhotoCard(photo, index);
    dom.photoGrid.appendChild(card);
  });

  // Pagination
  const hasMultiplePages = (photos.totalPages || 0) > 1;
  dom.paginationRow.style.display = hasMultiplePages ? 'flex' : 'none';

  if (hasMultiplePages) {
    const currentPage = photos.currentPage || 1;
    const totalPages = photos.totalPages || 1;
    dom.prevPageBtn.disabled = currentPage <= 1;
    dom.prevPageBtn.style.opacity = currentPage <= 1 ? '0.4' : '1';
    dom.nextPageBtn.disabled = currentPage >= totalPages;
    dom.nextPageBtn.style.opacity = currentPage >= totalPages ? '0.4' : '1';
  }
}

/**
 * Creates a photo card DOM element from a single photo data object.
 *
 * @param {object} photo - Photo data from valueStruct /photos/results[].
 * @param {number} index - Position in list (used for staggered animation delay).
 * @returns {HTMLElement} The constructed photo card article element.
 */
function renderPhotoCard(photo, index) {
  const template = dom.photoCardTemplate.content.cloneNode(true);
  const card = template.querySelector('.photo-card');

  card.style.animationDelay = `${index * 40}ms`;

  const img = card.querySelector('.photo-img');
  img.src = photo.url || '';
  img.alt = photo.description || photo.photographerName || 'Photo';

  const viewBtn = card.querySelector('.photo-view-btn');
  viewBtn.href = photo.profileUrl || '#';

  const nameEl = card.querySelector('.photographer-name');
  nameEl.textContent = photo.photographerName || 'Unknown';

  const tagsEl = card.querySelector('.photo-tags');
  tagsEl.textContent = photo.tags ? `#${photo.tags.split(',')[0].trim()}` : '';

  const descEl = card.querySelector('.photo-description');
  descEl.textContent = photo.description || '';

  return card;
}

// ---------------------------------------------------------------------------
// A2UI Inspector
// ---------------------------------------------------------------------------

/**
 * Populates the A2UI raw payload inspector panels.
 *
 * @param {Array}  a2uiMessages - Parsed A2UI message array.
 * @param {object} theme        - Extracted theme data.
 * @param {object} photos       - Extracted data model.
 */
function updateInspector(a2uiMessages, theme, photos) {
  if (!a2uiMessages) return;

  dom.inspectorPanel.style.display = 'flex';
  dom.rawJson.textContent = JSON.stringify(a2uiMessages, null, 2);
  dom.themeJson.textContent = JSON.stringify(theme, null, 2);
  dom.dataJson.textContent = JSON.stringify({ photos }, null, 2);
}

// Inspector toggle
dom.inspectorToggle.addEventListener('click', () => {
  const isOpen = dom.inspectorBody.style.display !== 'none';
  dom.inspectorBody.style.display = isOpen ? 'none' : 'flex';
  dom.inspectorChevron.classList.toggle('open', !isOpen);
});

// Inspector tabs
document.querySelectorAll('.itab').forEach((tab) => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.target;
    document.querySelectorAll('.itab').forEach((t) => t.classList.remove('active'));
    tab.classList.add('active');
    ['rawJson', 'themeJson', 'dataJson'].forEach((id) => {
      $(id).style.display = id === target ? 'block' : 'none';
    });
  });
});

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

dom.prevPageBtn.addEventListener('click', () => {
  if (state.prevPagePrompt) sendMessage(state.prevPagePrompt);
});

dom.nextPageBtn.addEventListener('click', () => {
  if (state.nextPagePrompt) sendMessage(state.nextPagePrompt);
});

// ---------------------------------------------------------------------------
// Suggestion Chips
// ---------------------------------------------------------------------------

dom.suggestionChips.querySelectorAll('.chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    const msg = chip.dataset.msg;
    if (msg) sendMessage(msg);
  });
});

// ---------------------------------------------------------------------------
// Agent Communication
// ---------------------------------------------------------------------------

/**
 * Sends a message to the A2A agent via the /api/chat proxy endpoint,
 * then renders the A2UI response.
 *
 * @param {string} message - User's natural language message.
 */
async function sendMessage(message) {
  if (state.isLoading || !message.trim()) return;

  state.isLoading = true;
  dom.sendBtn.disabled = true;
  dom.loadingOverlay.style.display = 'flex';
  dom.chatInput.value = '';

  addChatBubble(message, 'user');

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: state.sessionId,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errText}`);
    }

    const data = await response.json();

    // Show agent text response
    const hasA2ui = Boolean(data.a2ui && data.a2ui.length > 0);
    addChatBubble(data.message, 'agent', hasA2ui);

    if (data.error) {
      addChatBubble(`A2UI parse error: ${data.error}`, 'error');
    }

    // Render A2UI output
    if (data.photos && data.photos.results) {
      renderGallery(data.photos, data.theme || state.theme);
    }

    // Update inspector
    if (data.a2ui) {
      updateInspector(data.a2ui, data.theme, data.photos);
    }

    // Mark agent as online
    dom.agentStatus.className = 'status-dot online';

  } catch (err) {
    console.error('Chat error:', err);
    addChatBubble(`Error: ${err.message}`, 'error');
    dom.agentStatus.className = 'status-dot error';
  } finally {
    state.isLoading = false;
    dom.sendBtn.disabled = false;
    dom.loadingOverlay.style.display = 'none';
    dom.chatInput.focus();
  }
}

// ---------------------------------------------------------------------------
// Form Submit
// ---------------------------------------------------------------------------

dom.chatForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const message = dom.chatInput.value.trim();
  if (message) sendMessage(message);
});

// ---------------------------------------------------------------------------
// Agent Health Check
// ---------------------------------------------------------------------------

async function checkAgentHealth() {
  try {
    const response = await fetch('/health', { signal: AbortSignal.timeout(5000) });
    if (response.ok) {
      dom.agentStatus.className = 'status-dot online';
    } else {
      dom.agentStatus.className = 'status-dot error';
    }
  } catch {
    dom.agentStatus.className = 'status-dot error';
  }
}

checkAgentHealth();
