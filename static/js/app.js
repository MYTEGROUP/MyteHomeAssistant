if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/js/service_worker.js')
    .then(() => console.log('Service Worker Registered'));
}
