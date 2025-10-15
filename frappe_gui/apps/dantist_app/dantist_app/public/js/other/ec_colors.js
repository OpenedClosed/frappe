// Global palette for Engagement Case UI
// Will define window.EC_COLORS only once.
(function (w) {
  if (w.EC_COLORS) return;

  w.EC_COLORS = {
    crm_status: {
      "New": "blue",
      "Qualification": "purple",
      "Briefing": "light-blue",
      "In Work": "green",
      "On Hold": "orange",
      "Won": "green",
      "Lost": "red",
      "Archived": "gray",
    },
    priority: {
      "Low": "gray",
      "Normal": "blue",
      "High": "orange",
      "Urgent": "red",
    },
    runtime_status: {
      "New Session": "blue",
      "Brief In Progress": "purple",
      "Brief Completed": "green",
      "Waiting for AI": "yellow",
      "Waiting for Client (AI)": "yellow",
      "Waiting for Consultant": "orange",
      "Read by Consultant": "light-blue",
      "Waiting for Client": "orange",
      "Closed – No Messages": "gray",
      "Closed by Timeout": "gray",
      "Closed by Operator": "green",
    },
    platform: {
      "Internal": "gray",
      "Instagram": "purple",
      "Facebook": "blue",
      "WhatsApp": "green",
      "Telegram": "light-blue",
      "Telegram Mini-App": "light-blue",
      "Telephony": "blue",
      "SMS": "yellow",
      "Email": "purple",
    },
    channel_type: {
      "Chat": "blue",
      "Call": "green",
      "SMS": "yellow",
      "Email": "purple",
      "Web Form": "light-blue",
    }
  };
})(window);