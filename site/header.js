// header.js
function loadHeader() {
  const API_BASE =
    typeof API_BASE_URL !== "undefined" && API_BASE_URL !== "__API_BASE_URL__"
      ? `${API_BASE_URL}/api/papers`
      : "http://localhost:8000/api/papers";
  const API_ROOT =
    typeof API_BASE_URL !== "undefined" && API_BASE_URL !== "__API_BASE_URL__"
      ? API_BASE_URL
      : "http://localhost:8000";

  const headerHTML = `
      <div class="navbar bg-primary neutral text-neutral-content shadow-lg">
        <div class="flex-1">
          <a href="base.html" class="btn btn-ghost normal-case text-xl">JournalClub</a>
        </div>
        <div class="flex-none gap-2">
          <a href="base.html?page=active-papers" class="btn btn-ghost btn-sm">Active Papers</a>
          <a href="base.html?page=topics" class="btn btn-ghost btn-sm">Topics</a>
          <a href="base.html?page=docs" class="btn btn-ghost btn-sm">Documentation</a>
          <a href="" id="apiSpecLink" class="btn btn-ghost btn-sm">API Spec</a>
          <a href="" id="swaggerLink" class="btn btn-ghost btn-sm">Swagger UI</a>
            <a href="base.html?page=podcast-builder" class="btn btn-ghost btn-sm gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ff8c00" class="w-4 h-4">
                        <circle cx="6.18" cy="17.82" r="2.18"/>
                        <path d="M4 4.44v2.83c7.03 0 12.73 5.7 12.73 12.73h2.83c0-8.59-6.97-15.56-15.56-15.56zm0 5.66v2.83c3.9 0 7.07 3.17 7.07 7.07h2.83c0-5.47-4.43-9.9-9.9-9.9z"/>
                    </svg>
                    RSS Feed
                </a>
            </div>
        </div>
    `;

  // Insert header at the beginning of body
  document.body.insertAdjacentHTML("afterbegin", headerHTML);
  // wire up API links (use API_ROOT to build absolute URLs)
  try {
    const apiSpec = document.getElementById("apiSpecLink");
    const swagger = document.getElementById("swaggerLink");
    if (apiSpec) apiSpec.setAttribute("href", `${API_ROOT}/docs`);
    if (swagger) swagger.setAttribute("href", `${API_ROOT}/swagger-ui`);
  } catch (e) {
    // ignore DOM wiring errors
  }
}

// Load header when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", loadHeader);
} else {
  loadHeader();
}
