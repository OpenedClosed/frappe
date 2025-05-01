(function () {
  let container, iframe;

  function injectIframe() {
    container = document.createElement('div');
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
    container.style.overflow = 'hidden'; // prevent scrollbars
    container.style.width = '162px';
    container.style.height = '62px';

    iframe = document.createElement('iframe');
    iframe.src = 'http://localhost:4000/chats/chat/';
    iframe.style.border = 'none';
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.pointerEvents = 'auto';

    container.appendChild(iframe);
    document.body.appendChild(container);
  }

  // Listen for size messages from iframe
  window.addEventListener('message', (event) => {
      console.log('Received message from iframe:', event.data);
      if(!event.data || !event.data.typ && event.data.type !== 'bgSize') {
        return;
      }
      const { height, width, showChat } = event.data || {};
      console.log('Height:', event.data.height, 'Width:', event.data.width);

      let timeout = showChat ? 0 : 500;
      setTimeout(() => {
        if (height) {
          container.style.height = `${height}px`;
          iframe.style.height = '100%';
        }
        if (width) {
          container.style.width = `${width}px`;
          iframe.style.width = '100%';
        }
      }, timeout);
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectIframe);
  } else {
    injectIframe();
  }

  window.addEventListener('focus', () => {
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.location.reload();
    }
  });
})();
