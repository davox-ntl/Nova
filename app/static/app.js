const state = {
  languages: [],
  voices: [],
  voice: null,
  context: 'quotidien',
  recognition: null,
  listening: false,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const sourceSelect = $('#source-language');
const targetSelect = $('#target-language');
const voiceSelect = $('#voice-select');
const sourceText = $('#source-text');
const form = $('#translation-form');
const conversation = $('#conversation');
const emptyConversation = $('#conversation-empty');
const translateButton = $('#translate-button');
const micButton = $('#mic-button');
const toast = $('#toast');
const onboarding = $('#onboarding-dialog');

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(() => toast.classList.remove('show'), 3300);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = 'Une erreur est survenue.';
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (_) { /* réponse non JSON */ }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function languageName(code) {
  return state.languages.find((language) => language.code === code)?.name || code;
}

function populateLanguages() {
  for (const select of [sourceSelect, targetSelect]) {
    select.replaceChildren();
    state.languages.forEach((language) => {
      const option = document.createElement('option');
      option.value = language.code;
      option.textContent = language.name;
      select.append(option);
    });
  }
  sourceSelect.value = localStorage.getItem('nova-source') || 'fr';
  targetSelect.value = localStorage.getItem('nova-target') || 'dyu';
  if (sourceSelect.value === targetSelect.value && state.languages.length > 1) {
    targetSelect.value = state.languages[1].code;
  }
}

function updateLanguagePreferences() {
  localStorage.setItem('nova-source', sourceSelect.value);
  localStorage.setItem('nova-target', targetSelect.value);
}

function populateVoices() {
  voiceSelect.replaceChildren();
  state.voices.forEach((voice) => {
    const option = document.createElement('option');
    option.value = voice.id;
    option.textContent = voice.name;
    voiceSelect.append(option);
  });
  const saved = localStorage.getItem('nova-voice');
  state.voice = state.voices.find((voice) => voice.id === saved)?.id
    || state.voices.find((voice) => voice.default)?.id
    || state.voices[0]?.id
    || null;
  if (state.voice) voiceSelect.value = state.voice;
}

function iconButton(label, symbol, handler) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'mini-button';
  button.textContent = `${symbol} ${label}`;
  button.addEventListener('click', handler);
  return button;
}

function appendMessage(kind, text, language, translationId = null, phonetic = '', references = []) {
  emptyConversation?.remove();
  const article = document.createElement('article');
  article.className = `message message--${kind}`;

  const meta = document.createElement('div');
  meta.className = 'message-meta';
  meta.textContent = kind === 'source' ? `Vous · ${language}` : `NOVA · ${language}`;
  if (references.length) {
    const badge = document.createElement('span');
    badge.className = 'index-badge';
    badge.textContent = `📖 ${references.length} extrait(s) d’index`;
    badge.title = references.map((item) => `${item.file} p. ${item.page}`).join('\n');
    meta.append(badge);
  }

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  if (phonetic) {
    const pronunciation = document.createElement('p');
    pronunciation.className = 'phonetic';
    pronunciation.textContent = `Prononciation : ${phonetic}`;
    bubble.after(pronunciation);
  }

  const actions = document.createElement('div');
  actions.className = 'message-actions';
  if (kind === 'target') {
    actions.append(
      iconButton('Écouter', '▶', () => speak(text, targetSelect.value)),
      iconButton('Copier', '⧉', async () => {
        try {
          await navigator.clipboard.writeText(text);
          showToast('Traduction copiée.');
        } catch (_) {
          showToast('La copie n’est pas autorisée dans ce navigateur.');
        }
      }),
    );
    if (translationId) {
      actions.append(iconButton('Utile', '♡', () => sendFeedback(translationId, true)));
    }
  }

  article.append(meta, bubble);
  if (actions.childNodes.length) article.append(actions);
  conversation.append(article);
  conversation.scrollTop = conversation.scrollHeight;
}

function appendWarning(text) {
  const warning = document.createElement('aside');
  warning.className = 'message-warning';
  warning.textContent = text;
  conversation.append(warning);
  conversation.scrollTop = conversation.scrollHeight;
}

function addTyping() {
  const typing = document.createElement('div');
  typing.className = 'typing';
  typing.id = 'typing-indicator';
  typing.setAttribute('aria-label', 'NOVA prépare la traduction');
  typing.innerHTML = '<i></i><i></i><i></i>';
  conversation.append(typing);
  conversation.scrollTop = conversation.scrollHeight;
}

async function sendFeedback(translationId, helpful) {
  try {
    await api('/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ translation_id: translationId, helpful }),
    });
    showToast('Merci, votre retour aide à améliorer NOVA.');
  } catch (error) {
    showToast(error.message);
  }
}

let audioPlayer = null;

function softBrowserVoice(lang) {
  const voices = window.speechSynthesis?.getVoices() || [];
  const sameLanguage = voices.filter((voice) => voice.lang.toLowerCase().startsWith(lang.slice(0, 2)));
  const preferred = ['vivienne', 'denise', 'français', 'french', 'natural'];
  for (const name of preferred) {
    const match = sameLanguage.find((voice) => voice.name.toLowerCase().includes(name));
    if (match) return match;
  }
  return sameLanguage[0] || null;
}

function speakWithBrowser(text, code) {
  if (!('speechSynthesis' in window)) {
    showToast('La lecture vocale n’est pas disponible sur ce navigateur.');
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  const lang = state.languages.find((language) => language.code === code)?.speech || 'fr-FR';
  utterance.lang = lang;
  utterance.voice = softBrowserVoice(lang);
  utterance.rate = 0.9;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

async function speak(text, code) {
  if (!text) return;
  if (audioPlayer) {
    audioPlayer.pause();
    audioPlayer = null;
  }
  const voice = state.voice || 'fr-FR-VivienneNeural';
  const voiceName = state.voices.find((item) => item.id === voice)?.name || 'voix douce';
  try {
    const params = new URLSearchParams({ text, voice });
    const response = await fetch(`/api/tts?${params.toString()}`);
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail || `HTTP ${response.status}`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const player = new Audio(url);
    player.onended = () => URL.revokeObjectURL(url);
    audioPlayer = player;
    await player.play();
    showToast(`Lecture Edge TTS · ${voiceName}`);
  } catch (error) {
    // Le repli est annoncé : l'utilisateur sait s'il n'écoute pas la voix neuronale.
    showToast(`Edge TTS indisponible (${error.message}). Voix système utilisée.`);
    speakWithBrowser(text, code);
  }
}

async function translateMessage(event) {
  event.preventDefault();
  const text = sourceText.value.trim();
  if (!text) return;
  if (sourceSelect.value === targetSelect.value) {
    showToast('Choisissez deux langues différentes.');
    targetSelect.focus();
    return;
  }

  updateLanguagePreferences();
  appendMessage('source', text, languageName(sourceSelect.value));
  addTyping();
  translateButton.disabled = true;
  translateButton.querySelector('span').textContent = 'Traduction…';

  try {
    const result = await api('/api/translations', {
      method: 'POST',
      body: JSON.stringify({
        source_language: sourceSelect.value,
        target_language: targetSelect.value,
        text,
        context: state.context,
      }),
    });
    $('#typing-indicator')?.remove();
    appendMessage(
      'target',
      result.translated_text,
      languageName(result.target_language),
      result.id,
      result.phonetic,
      result.references || [],
    );
    if (result.warning) appendWarning(result.warning);
    sourceText.value = '';
    $('#char-count').textContent = '0';
  } catch (error) {
    $('#typing-indicator')?.remove();
    appendWarning(`Échec de la traduction : ${error.message}`);
  } finally {
    translateButton.disabled = false;
    translateButton.querySelector('span').textContent = 'Traduire';
    sourceText.focus();
  }
}

function setView(name) {
  $$('.view').forEach((view) => {
    const selected = view.id === `view-${name}`;
    view.hidden = !selected;
    view.classList.toggle('is-visible', selected);
  });
  $$('[data-view]').forEach((button) => {
    const selected = button.dataset.view === name;
    button.classList.toggle('is-active', selected);
    if (button.closest('.sidebar')) {
      selected ? button.setAttribute('aria-current', 'page') : button.removeAttribute('aria-current');
    }
  });
  if (name === 'history') loadHistory();
  const title = $(`#view-${name} h1`);
  title?.setAttribute('tabindex', '-1');
  title?.focus({ preventScroll: true });
  history.replaceState(null, '', `#${name === 'translate' ? 'traduire' : name}`);
}

async function loadHistory() {
  const list = $('#history-list');
  list.innerHTML = '<div class="empty-state">Chargement de l’historique…</div>';
  try {
    const entries = await api('/api/translations?limit=50');
    list.replaceChildren();
    if (!entries.length) {
      list.innerHTML = '<div class="empty-state"><strong>Aucune traduction pour le moment.</strong><br>Votre prochain échange apparaîtra ici.</div>';
      return;
    }
    entries.forEach((entry) => {
      const card = document.createElement('article');
      card.className = 'history-card';
      const top = document.createElement('div');
      top.className = 'history-top';
      const languages = document.createElement('span');
      languages.className = 'history-languages';
      languages.textContent = `${languageName(entry.source_language)} → ${languageName(entry.target_language)}`;
      const date = document.createElement('time');
      date.className = 'history-date';
      date.textContent = new Date(`${entry.created_at}Z`).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' });
      top.append(languages, date);
      const pair = document.createElement('div');
      pair.className = 'history-pair';
      const source = document.createElement('p');
      source.textContent = entry.source_text;
      const arrow = document.createElement('span');
      arrow.textContent = '→';
      const targetColumn = document.createElement('div');
      const target = document.createElement('p');
      target.textContent = entry.translated_text;
      targetColumn.append(target);
      if (entry.phonetic) {
        const pronunciation = document.createElement('p');
        pronunciation.className = 'phonetic';
        pronunciation.textContent = `Prononciation : ${entry.phonetic}`;
        targetColumn.append(pronunciation);
      }
      pair.append(source, arrow, targetColumn);
      card.append(top, pair);
      list.append(card);
    });
  } catch (error) {
    list.innerHTML = `<div class="empty-state">${error.message}</div>`;
  }
}

function configureSpeechRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    micButton.title = 'Dictée indisponible sur ce navigateur';
    return;
  }
  state.recognition = new Recognition();
  state.recognition.interimResults = true;
  state.recognition.continuous = false;
  state.recognition.onstart = () => {
    state.listening = true;
    micButton.setAttribute('aria-pressed', 'true');
    showToast('Je vous écoute…');
  };
  state.recognition.onresult = (event) => {
    sourceText.value = [...event.results].map((result) => result[0].transcript).join('');
    $('#char-count').textContent = sourceText.value.length;
  };
  state.recognition.onerror = () => showToast('Impossible d’utiliser le micro. Vérifiez l’autorisation.');
  state.recognition.onend = () => {
    state.listening = false;
    micButton.setAttribute('aria-pressed', 'false');
  };
}

function toggleListening() {
  if (!state.recognition) {
    showToast('La dictée vocale n’est pas disponible sur ce navigateur.');
    return;
  }
  if (state.listening) {
    state.recognition.stop();
  } else {
    state.recognition.lang = state.languages.find((language) => language.code === sourceSelect.value)?.speech || 'fr-FR';
    state.recognition.start();
  }
}

async function initialise() {
  try {
    const [languages, , voices] = await Promise.all([
      api('/api/languages'),
      api('/api/health').then((health) => {
        const labels = { nvidia: 'DeepSeek via NVIDIA actif', deepseek: 'Moteur DeepSeek actif', gemini: 'Moteur Gemini actif' };
        $('#engine-status').textContent = labels[health.translation_engine] || 'Mode démonstration local';
      }),
      api('/api/voices'),
    ]);
    state.languages = languages;
    state.voices = voices;
    populateLanguages();
    populateVoices();
  } catch (error) {
    showToast(`Connexion au serveur impossible : ${error.message}`);
  }
  configureSpeechRecognition();

  const route = location.hash.replace('#', '');
  if (route === 'history' || route === 'guide') setView(route);
  if (!localStorage.getItem('nova-onboarding-complete')) onboarding.showModal();
}

form.addEventListener('submit', translateMessage);
sourceText.addEventListener('input', () => { $('#char-count').textContent = sourceText.value.length; });
sourceText.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') form.requestSubmit();
});
sourceSelect.addEventListener('change', updateLanguagePreferences);
targetSelect.addEventListener('change', updateLanguagePreferences);
voiceSelect.addEventListener('change', () => {
  state.voice = voiceSelect.value;
  localStorage.setItem('nova-voice', state.voice);
});
$('#swap-languages').addEventListener('click', () => {
  const current = sourceSelect.value;
  sourceSelect.value = targetSelect.value;
  targetSelect.value = current;
  updateLanguagePreferences();
});
$$('.context-chip').forEach((chip) => chip.addEventListener('click', () => {
  state.context = chip.dataset.context;
  $$('.context-chip').forEach((item) => {
    const selected = item === chip;
    item.classList.toggle('is-active', selected);
    item.setAttribute('aria-checked', String(selected));
  });
}));
$$('[data-view]').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
$$('[data-view-link]').forEach((link) => link.addEventListener('click', (event) => { event.preventDefault(); setView(link.dataset.viewLink); }));
$('#help-button').addEventListener('click', () => setView('guide'));
$('#clear-history').addEventListener('click', async () => {
  if (!confirm('Effacer tout l’historique de démonstration ?')) return;
  try {
    await api('/api/translations', { method: 'DELETE' });
    await loadHistory();
    showToast('Historique effacé.');
  } catch (error) { showToast(error.message); }
});
micButton.addEventListener('click', toggleListening);
$('#open-onboarding').addEventListener('click', () => onboarding.showModal());
$('#close-onboarding').addEventListener('click', () => onboarding.close());
$('#start-nova').addEventListener('click', () => {
  localStorage.setItem('nova-onboarding-complete', 'true');
  onboarding.close();
  sourceText.focus();
});
onboarding.addEventListener('click', (event) => {
  const rectangle = onboarding.getBoundingClientRect();
  const outside = event.clientX < rectangle.left || event.clientX > rectangle.right || event.clientY < rectangle.top || event.clientY > rectangle.bottom;
  if (outside) onboarding.close();
});

initialise();
