<!-- File: InlineList.vue -->
<template>
    <div>
      <!-- Display each item (e.g. ChatMessage) -->
      <table class="table-auto w-full border-collapse">
        <thead>
          <tr>
            <th v-for="field in inlineDef.fields" :key="field.name" class="border p-2">
              {{ field.title.en || field.name }}
            </th>
            <th class="border p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(childItem, index) in items" :key="index" class="border">
            <td
              v-for="field in inlineDef.fields"
              :key="field.name"
              class="border p-2"
            >
              <!-- If readOnly or field.read_only, just show data -->
              <span v-if="isFieldReadOnly(field)">
                {{ childItem[field.name] }}
              </span>
              <!-- Else allow inline editing (InputText, etc) -->
              <template v-else>
                <input
                  class="border w-full px-2 py-1"
                  v-model="childItem[field.name]"
                  :disabled="readOnly"
                />
              </template>
            </td>
            <td class="border p-2 text-center">
              <button
                v-if="!readOnly"
                class="p-1 text-blue-500"
                @click="updateChild(childItem)"
              >
                Save
              </button>
              <button
                v-if="!readOnly"
                class="p-1 text-red-500 ml-2"
                @click="deleteChild(childItem)"
              >
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
  
      <!-- Create new inline item -->
      <div v-if="!readOnly" class="mt-4">
        <h4 class="font-semibold">Add New</h4>
        <div class="flex gap-4">
          <div v-for="field in inlineDef.fields" :key="field.name" class="flex flex-col">
            <label class="font-semibold text-sm">
              {{ field.title.en || field.name }}
            </label>
            <input
              v-model="newItem[field.name]"
              class="border px-2 py-1 w-full"
              :disabled="field.read_only"
            />
          </div>
        </div>
        <button class="mt-2 p-2 bg-green-500 text-white" @click="createChild">
          Create
        </button>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, watch, toRefs } from "vue";
  import { useNuxtApp } from "#imports";
  
  const props = defineProps({
    inlineDef: { type: Object, required: true },
    parentEntity: { type: String, required: true },
    parentId: { type: String, required: true },
    items: { type: Array, default: () => [] },
    readOnly: { type: Boolean, default: false }
  });
  
  const emit = defineEmits(["reloadParent"]);
  
  // We'll keep a local copy of the items array if you want to edit "locally"
  const localItems = ref(props.items ? [...props.items] : []);
  watch(
    () => props.items,
    (newVal) => {
      localItems.value = [...newVal];
    }
  );
  
  // For creating a new inline record:
  const newItem = ref({});
  
  /**
   * Decide if a field is effectively read-only
   * (because it's read_only in config or the parent form is readOnly).
   */
  function isFieldReadOnly(field) {
    return field.read_only === true || props.readOnly;
  }
  
  const nuxtApp = useNuxtApp();
  
  /**
   * Update an existing inline item via `PATCH`.
   * Typically you have a separate route for the inline entity (e.g. `chat_messages`).
   */
  async function updateChild(childItem) {
    try {
      // Suppose the inline entity is "chat_messages".
      // We need to find the route or ID for the child record
      // Often the child has its own "id". Check your data structure for the actual key.
      if (!childItem.id) {
        alert("No ID found on inline item!");
        return;
      }
  
      await nuxtApp.$api.patch(`api/admin/${props.inlineDef.name.toLowerCase()}s/${childItem.id}`, childItem);
      alert("Inline item updated!");
      emit("reloadParent");
    } catch (error) {
      console.error(error);
      alert("Error updating inline");
    }
  }
  
  /**
   * Delete inline item via `DELETE`.
   */
  async function deleteChild(childItem) {
    try {
      if (!childItem.id) {
        alert("No ID found on inline item!");
        return;
      }
      await nuxtApp.$api.delete(`api/admin/${props.inlineDef.name.toLowerCase()}s/${childItem.id}`);
      alert("Inline item deleted!");
      emit("reloadParent");
    } catch (error) {
      console.error(error);
      alert("Error deleting inline");
    }
  }
  
  /**
   * Create a new inline item. Often you'll want to pass the parent ID or foreign key.
   */
  async function createChild() {
    try {
      // Example: The ChatMessage might need the `chat_session_id` or something to link it to the parent.
      // Suppose the backend expects "chat_id" or "chat_session_id". 
      // Adjust this to match your actual foreign key field name.
      newItem.value.chat_session_id = props.parentId;
  
      await nuxtApp.$api.post(`api/admin/${props.inlineDef.name.toLowerCase()}s/`, newItem.value);
      alert("Inline item created!");
      newItem.value = {};
      emit("reloadParent");
    } catch (error) {
      console.error(error);
      alert("Error creating inline");
    }
  }
  </script>
  