import metadata from "metadata-scraper";

export default defineEventHandler(async (event) => {
  try {
    // Parse the incoming JSON body to get the URL
    const { url } = await readBody(event);

    if (!url) {
      return {
        success: false,
        message: "No URL provided",
      };
    }

    // Use metadata-scraper to fetch metadata (Open Graph, etc.)
    const data = await metadata(url);

    // Return the scraped data to the client
    return {
      success: true,
      data,
    };
  } catch (error) {
    console.error("metadata-scraper error:", error);
    return {
      success: false,
      message: "Failed to scrape metadata",
    };
  }
});
