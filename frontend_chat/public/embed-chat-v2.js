(function () {
    function injectIframe() {
      var iframe = document.createElement("iframe");
      
     
      // Set the iframe attributes
      iframe.src = `https://panamed-aihubworks.com/chats/chat/`;
      
      iframe.style.position = "fixed";
      iframe.style.top = "0";
      iframe.style.left = "0";
      iframe.style.width = "100vw";
      iframe.style.height = "100vh";
      iframe.style.border = "none";
      iframe.style.zIndex = "9999";
  
      // Append the iframe when the DOM is ready
      document.body.appendChild(iframe);
    }
  
    // Wait until the DOM is fully loaded
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", injectIframe);
    } else {
      injectIframe();
    }
  })();
  