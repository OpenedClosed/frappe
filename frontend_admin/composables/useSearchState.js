import { ref, computed } from 'vue';

/**
 * Composable for managing search state and functionality
 * @param {Object} options - Configuration options
 * @param {Function} options.searchHandler - Function to handle search operations
 * @param {Function} options.clearHandler - Function to handle search clearing
 */
export function useSearchState(options = {}) {
  const { searchHandler, clearHandler } = options;
  
  // Search state
  const searchQuery = ref('');
  const appliedSearch = ref({});
  const isSearching = ref(false);
  
  // Computed properties
  const hasActiveSearch = computed(() => {
    return appliedSearch.value?.q && appliedSearch.value.q.trim();
  });
  
  const searchParams = computed(() => {
    return appliedSearch.value;
  });
  
  // Search functions
  const performSearch = async (searchTerm) => {
    isSearching.value = true;
    
    try {
      if (!searchTerm || !searchTerm.trim()) {
        // Clear search
        appliedSearch.value = {};
        if (clearHandler) {
          await clearHandler();
        }
        return;
      }
      
      // Apply search
      const searchObj = { q: searchTerm.trim() };
      appliedSearch.value = searchObj;
      
      if (searchHandler) {
        await searchHandler(searchObj);
      }
    } catch (error) {
      console.error('Search operation failed:', error);
      throw error;
    } finally {
      isSearching.value = false;
    }
  };
  
  const clearSearch = async () => {
    searchQuery.value = '';
    appliedSearch.value = {};
    isSearching.value = false;
    
    if (clearHandler) {
      await clearHandler();
    }
  };
  
  const updateSearchQuery = (query) => {
    searchQuery.value = query;
  };
  
  return {
    // State
    searchQuery,
    appliedSearch,
    isSearching,
    
    // Computed
    hasActiveSearch,
    searchParams,
    
    // Methods
    performSearch,
    clearSearch,
    updateSearchQuery
  };
}