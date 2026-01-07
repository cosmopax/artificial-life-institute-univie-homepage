/**
 * Asset Optimization & Progressive Enhancement
 * Implements lazy loading and scroll reveal animations
 */

document.addEventListener('DOMContentLoaded', () => {
  
  // ==================== LAZY LOAD BACKGROUND IMAGES ====================
  const lazyBackgrounds = document.querySelectorAll('.card-bg[data-bg]');
  
  if ('IntersectionObserver' in window) {
    const bgObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const bg = entry.target;
          const bgUrl = bg.getAttribute('data-bg');
          
          // Preload the image
          const img = new Image();
          img.onload = () => {
            bg.style.backgroundImage = `url('${bgUrl}')`;
            bg.classList.add('loaded');
          };
          img.src = bgUrl;
          
          observer.unobserve(bg);
        }
      });
    }, {
      rootMargin: '50px' // Start loading 50px before entering viewport
    });
    
    lazyBackgrounds.forEach(bg => bgObserver.observe(bg));
  } else {
    // Fallback for older browsers
    lazyBackgrounds.forEach(bg => {
      const bgUrl = bg.getAttribute('data-bg');
      bg.style.backgroundImage = `url('${bgUrl}')`;
      bg.classList.add('loaded');
    });
  }
  
  // ==================== SCROLL REVEAL ANIMATION ====================
  const revealElements = document.querySelectorAll('.scroll-reveal');
  
  if ('IntersectionObserver' in window && revealElements.length > 0) {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          // Optional: unobserve after reveal (one-time animation)
          // revealObserver.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });
    
    revealElements.forEach(el => revealObserver.observe(el));
  } else {
    // Fallback: reveal all immediately
    revealElements.forEach(el => el.classList.add('revealed'));
  }
  
  // ==================== PERFORMANCE MONITORING ====================
  if (window.performance && window.performance.getEntriesByType) {
    window.addEventListener('load', () => {
      const perfData = window.performance.timing;
      const loadTime = perfData.loadEventEnd - perfData.navigationStart;
      
      // Log only in development (check for localhost or specific domains)
      if (window.location.hostname === 'localhost' || window.location.hostname.includes('127.0.0.1')) {
        console.log(`[Performance] Page load: ${loadTime}ms`);
        console.log(`[Performance] DOM ready: ${perfData.domContentLoadedEventEnd - perfData.navigationStart}ms`);
      }
    });
  }
});
