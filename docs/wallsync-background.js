(function () {
  'use strict';

  const STORAGE_KEY = 'wallsync-browser-wallpaper';
  const BUILTIN_WALLPAPERS = [
    'animenight.jpg',
    'decoration.jpg',
    'blackdots.jpg',
    'fullmoon.jpg'
  ];

  function setWallpaper(value, persist) {
    const wallpaperArea = document.querySelector('.bg');
    if (!wallpaperArea || !value) return;

    wallpaperArea.style.setProperty('--wallpaper-image', `url("${value}")`);

    if (persist) {
      try {
        localStorage.setItem(STORAGE_KEY, value);
      } catch (error) {
        console.warn('Could not save the browser wallpaper:', error);
      }
    }

    const select = document.getElementById('wallpaperSelect');
    if (select && BUILTIN_WALLPAPERS.includes(value)) {
      select.value = value;
    }
  }

  function readSavedWallpaper() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (error) {
      console.warn('Could not read the saved browser wallpaper:', error);
      return null;
    }
  }

  function applySavedWallpaper() {
    const params = new URLSearchParams(window.location.search);
    const linkedWallpaper = params.get('wallpaper');
    const savedWallpaper = readSavedWallpaper();
    const wallpaper = linkedWallpaper || savedWallpaper;

    if (wallpaper) setWallpaper(wallpaper, false);

    if (linkedWallpaper) {
      try {
        localStorage.setItem(STORAGE_KEY, linkedWallpaper);
      } catch (error) {
        console.warn('Could not save the linked browser wallpaper:', error);
      }
    }
  }

  function initializeControls() {
    const wallpaperSelect = document.getElementById('wallpaperSelect');
    const randomButton = document.getElementById('randomWallpaperButton');
    const upload = document.getElementById('wallpaperUpload');
    const urlInput = document.getElementById('wallpaperUrl');
    const applyUrlButton = document.getElementById('applyWallpaperUrl');
    const resetButton = document.getElementById('resetWallpaperButton');

    if (wallpaperSelect) {
      const savedWallpaper = readSavedWallpaper();
      if (BUILTIN_WALLPAPERS.includes(savedWallpaper)) {
        wallpaperSelect.value = savedWallpaper;
      }
      wallpaperSelect.addEventListener('change', () => setWallpaper(wallpaperSelect.value, true));
    }

    if (randomButton) {
      randomButton.addEventListener('click', function () {
        const current = wallpaperSelect ? wallpaperSelect.value : '';
        const candidates = BUILTIN_WALLPAPERS.filter(value => value !== current);
        setWallpaper(candidates[Math.floor(Math.random() * candidates.length)], true);
      });
    }

    if (upload) {
      upload.addEventListener('change', function () {
        const file = upload.files && upload.files[0];
        if (!file || !file.type.startsWith('image/')) return;
        if (file.size > 4 * 1024 * 1024) {
          alert('Please choose an image smaller than 4 MB.');
          upload.value = '';
          return;
        }
        const reader = new FileReader();
        reader.onload = () => setWallpaper(reader.result, true);
        reader.readAsDataURL(file);
      });
    }

    function applyLinkedUrl() {
      if (!urlInput) return;
      const value = urlInput.value.trim();
      if (!value) return;
      try {
        const url = new URL(value, window.location.href);
        if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Invalid protocol');
        setWallpaper(url.href, true);
        urlInput.value = '';
      } catch (error) {
        alert('Enter a valid HTTP or HTTPS image URL.');
      }
    }

    if (applyUrlButton) applyUrlButton.addEventListener('click', applyLinkedUrl);
    if (urlInput) {
      urlInput.addEventListener('keydown', event => {
        if (event.key === 'Enter') applyLinkedUrl();
      });
    }

    if (resetButton) {
      resetButton.addEventListener('click', function () {
        try {
          localStorage.removeItem(STORAGE_KEY);
        } catch (error) {
          console.warn('Could not remove the saved browser wallpaper:', error);
        }
        setWallpaper('animenight.jpg', false);
      });
    }
  }

  window.addEventListener('storage', event => {
    if (event.key === STORAGE_KEY) setWallpaper(event.newValue || 'animenight.jpg', false);
  });

  applySavedWallpaper();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeControls);
  } else {
    initializeControls();
  }
})();
