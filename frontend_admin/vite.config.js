// vite.config.js
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  define: {
    'process.env.NODE_ENV': '"production"',
  },
  build: {
    lib: {
      entry: './components/Chat/MainChat.vue', // Path to your main SFC
      name: 'MyComponent',
      fileName: (format) => `my-component.${format}.js`,
    },
    // If you want to bundle *everything*, do not list external dependencies:
    rollupOptions: {
      external: ['vue'],  
      output: {
        globals: { vue: 'Vue' },  
      },
    },
  },
  plugins: [vue()],
});
