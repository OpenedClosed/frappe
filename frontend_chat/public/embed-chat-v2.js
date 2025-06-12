(function () {
  let container, iframe;

  function isMobileDevice() {
    return window.innerWidth < 768;
  }

  function injectIframe() {
    container = document.createElement('div');
    iframe = document.createElement('iframe');

    // Set common iframe styles
    iframe.src = 'http://localhost:4000/chats/chat/';
    // iframe.src = `https://panamed-aihubworks.com/chats/chat/`;
    iframe.style.border = 'none';
    iframe.style.pointerEvents = 'auto';

    container.appendChild(iframe);
    document.body.appendChild(container);
    applyStyles(); // Apply initial styles
  }

  function applyStyles() {
    if (!container || !iframe) return;

    const mobile = isMobileDevice();

    if (mobile) {
      container.style.position = 'fixed';
      container.style.bottom = '0';
      container.style.right = '0';
      container.style.width = '162px';
      container.style.height = '62px';
      container.style.zIndex = '9999';
      container.style.background = 'transparent';
      container.style.pointerEvents = 'auto';
      container.style.overflow = 'hidden';

    
      iframe.style.width = '100%';
      iframe.style.height = '100%';
    } else {
      container.style.position = 'fixed';
      container.style.bottom = '20px';
      container.style.right = '20px';
      container.style.display = 'flex';
      container.style.flexDirection = 'column';
      container.style.zIndex = '9999';
      container.style.background = 'transparent';
      container.style.pointerEvents = 'auto';
      container.style.maxHeight = '90vh';
      container.style.maxWidth = '90vw';
      container.style.overflow = 'hidden';
      container.style.width = '162px';
      container.style.height = '162px';

      iframe.style.width = '100%';
      iframe.style.height = '100%';
    }
  }

  // Handle dynamic resizing
  window.addEventListener('resize', () => {
    applyStyles();
  });

  // Handle messages from iframe
  window.addEventListener('message', (event) => {
    if (!event.data || (event.data.type !== 'bgSize')) {
      return;
    }

    const { height, width, showChat } = event.data || {};
    let timeout = showChat ? 0 : 500;

    setTimeout(() => {
      if (!isMobileDevice()) {
        if (height) {
          container.style.height = `${height}px`;
        }
        if (width) {
          container.style.width = `${width}px`;
        }
      } else {
      if (showChat) {
        container.style.height = '100vh';
        container.style.width = '100vw';
      }else {
        container.style.width = '162px';
        container.style.height = '162px';
      }
      }
    
    }, timeout);
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectIframe);
  } else {
    injectIframe();
  }
  // Reload iframe on focus
  window.addEventListener('focus', () => {
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.location.reload();
    }
  });
})();
