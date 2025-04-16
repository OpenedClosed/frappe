export default defineAppConfig({
  umami: {
    host: "",
    id: "",
    autoTrack: true,
    version: 2,
    useDirective: true,
    debug: true,
    customEndpoint: "/umami/api/send",
  },
});
