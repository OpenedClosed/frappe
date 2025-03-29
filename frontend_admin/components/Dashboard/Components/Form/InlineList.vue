<template>
  <div>
    <!-- Existing inline items -->
    <div
      v-for="(childItem, index) in localItems"
      :key="index"
      class="mb-4 border p-4 rounded"
    >
      <h4 class="font-semibold mb-2">
        <!-- {{ inlineDef.verbose_name }} -->
        {{ inlineDef.verbose_name[currentLanguage] || inlineDef.verbose_name?.en || " "  }} #{{ index + 1 }}
      </h4>

      <!-- Use DynamicForm to render each inline item -->
      <DynamicForm
        :fields="inlineDef.fields"
        :modelValue="childItem"
        :readOnly="readOnly"
        @update:modelValue="(updated) => updateLocalItem(index, updated)"
      />
      <!-- {{ inlineDef }} -->

      <!-- Actions: Save / Delete (only if not readOnly) -->
      <div class="flex gap-2 mt-2" v-if="!readOnly">
        <button
          class="p-2 bg-blue-500 text-white rounded"
          @click="saveOneInline(index)"
        >
        Save
        </button>
        <button
          class="p-2 bg-red-500 text-white rounded"
          @click="deleteOneInline(index)"
        >
        Delete
        </button>
      </div>
    </div>

    <!-- Create new inline item -->
   <!-- Create new inline item (Only show if inline_type is "list" or no existing single item) -->
<div v-if="!readOnly && (props.inlineDef.inline_type === 'list' || localItems.length === 0)" class="mt-4 p-4 border rounded">
  <h4 class="font-semibold mb-2">Add New</h4>

  <!-- DynamicForm for new item -->
  <DynamicForm
    :fields="props.inlineDef.fields"
    :modelValue="newItem"
    @update:modelValue="(updated) => (newItem = updated)"
  />

  <button
    class="mt-2 p-2 bg-green-500 text-white rounded"
    @click="addNewInline"
  >
  Create
  </button>
</div>

  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useNuxtApp, useRoute } from "#imports";
import DynamicForm from "~/components/Dashboard/Components/Form/DynamicForm.vue";
const { currentLanguage } = useLanguageState();
/**
 * Props:
 * - `inlineDef` includes info about how to render these inline items
 *   (fields, name, possibly the key where these items live in the parent object).
 * - `parentEntity` and `parentId` indicate which parent resource we're patching.
 * - `items` is the array of inline items (stored on the parent).
 * - `readOnly` indicates if the user can edit these items.
 */
const props = defineProps({
  inlineDef: { type: Object, required: true },
  parentEntity: { type: String, required: true },
  parentId: { type: String, required: true },
  items: { type: Array, default: () => [] },
  readOnly: { type: Boolean, default: false },
});


console.log("inlineDef", props.inlineDef);
console.log("items", props.items);
const emit = defineEmits(["reloadParent"]);

const nuxtApp = useNuxtApp();
const route = useRoute();

// Local copy of the inline items array
const localItems = ref([...props.items]);

// Whenever parent `items` changes, update localItems
watch(
  () => props.items,
  (newVal) => {
    localItems.value = [...newVal];
  }
);

/**
 * Returns an object containing only the fields that have changed
 * between originalItem and updatedItem, plus the item's 'id' if present.
 */
function getChangedFields(originalItem, updatedItem) {
  const diff = {};

  // Always include `id` so the server knows which record we're updating
  if (updatedItem.id) {
    diff.id = updatedItem.id;
  }

  // Compare each key in the updatedItem
  for (const key in updatedItem) {
    if (updatedItem[key] !== originalItem[key]) {
      diff[key] = updatedItem[key];
    }
  }

  return diff;
}


// For creating a new inline record
const newItem = ref({});

/**
 * Helper method to update an item in our local array state.
 */
function updateLocalItem(index, updated) {
  localItems.value[index] = { ...updated };
}

const { currentPageName } = usePageState()
/**
 * For "Save" of one inline item:
 *  - We already have `localItems` with the user changes.
 *  - Typically we patch the *parent* item with the updated array.
 */
 async function saveOneInline(index) {
  try {
    const updatedItem = localItems.value[index];
    const originalItem = props.items[index] || {};

    // Build an object of only the changed fields
    const changes = getChangedFields(originalItem, updatedItem);

    if (Object.keys(changes).length === 1 && changes.id) {
      alert("No changes detected.");
      return;
    }

    // Prepare data format based on inline_type
    const patchData = {
      [props.inlineDef.field]: props.inlineDef.inline_type === "single"
        ? changes // Send single object
        : [changes], // Send array
    };

    await nuxtApp.$api.patch(
      `api/${currentPageName.value}/${props.parentEntity}/${props.parentId}`,
      patchData
    );

    alert("Inline item updated!");
    emit("reloadParent");
  } catch (error) {
    console.error("Error saving inline item:", error);
    alert("Error updating inline item.");
  }
}



/**
 * For "Delete" of one inline item:
 *  - Remove that item from localItems
 *  - Patch the parent with the updated array
 */
async function deleteOneInline(index) {
  // Optional: confirm before deleting
  const confirmation = confirm("Are you sure you want to delete this item?");
  if (!confirmation) return;

  try {
    // Remove the item from the array
    localItems.value.splice(index, 1);

    // Patch the parent with the updated array
    const patchData = {
      [props.inlineDef.field]: [...localItems.value],
    };

    await nuxtApp.$api.patch(
      `api/${currentPageName.value}/${props.parentEntity}/${props.parentId}`,
      patchData
    );

    alert("Inline item deleted (via parent PATCH)!");
    emit("reloadParent");
  } catch (error) {
    console.error("Error deleting inline item:", error);
    alert("Error deleting inline item.");
  }
}

/**
 * For creating a new inline item:
 *  - Push the new item into localItems
 *  - Patch the parent with the updated array
 */
 async function addNewInline() {
  try {
    // Prevent adding more than 1 element if inline_type is "single"
    if (props.inlineDef.inline_type === "single" && localItems.value.length >= 1) {
      alert("Only one item is allowed.");
      return;
    }

    // Push to the local array
    localItems.value.push({ ...newItem.value });

    // Prepare the correct data format based on inline_type
    const patchData = {
      [props.inlineDef.field]: props.inlineDef.inline_type === "single"
        ? localItems.value[0] // Send single object
        : [...localItems.value], // Send array
    };

    await nuxtApp.$api.patch(
      `api/${currentPageName.value}/${props.parentEntity}/${props.parentId}`,
      patchData
    );

    // Clear the create form
    newItem.value = {};
    alert("Inline item created!");
    emit("reloadParent");
  } catch (error) {
    console.error("Error creating inline item:", error);
    alert("Error creating inline item.");
  }
}

</script>