document.addEventListener('DOMContentLoaded', () => {
  const config = window.dashboardConfig;
  if (!config || !config.apiUrl) {
    return;
  }

  fetch(config.apiUrl)
    .then((response) => response.json())
    .then((data) => {
      const priorityCtx = document.getElementById('priorityChart');
      const statusCtx = document.getElementById('statusChart');
      const notificationList = document.getElementById('notificationList');

      if (priorityCtx) {
        new Chart(priorityCtx, {
          type: 'bar',
          data: {
            labels: ['Alta prioridad', 'Media prioridad', 'Baja prioridad'],
            datasets: [{
              label: 'Trámites',
              data: [
                data.prioridades['Alta prioridad'] || 0,
                data.prioridades['Media prioridad'] || 0,
                data.prioridades['Baja prioridad'] || 0,
              ],
              backgroundColor: ['#dc2626', '#f59e0b', '#22c55e'],
              borderRadius: 12,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
            },
            scales: {
              y: { beginAtZero: true, ticks: { precision: 0 } },
            },
          },
        });
      }

      if (statusCtx) {
        new Chart(statusCtx, {
          type: 'doughnut',
          data: {
            labels: ['Recibido', 'En Proceso', 'Observado', 'Finalizado'],
            datasets: [{
              data: [
                data.estados['Recibido'] || 0,
                data.estados['En Proceso'] || 0,
                data.estados['Observado'] || 0,
                data.estados['Finalizado'] || 0,
              ],
              backgroundColor: ['#3b82f6', '#8b5cf6', '#f97316', '#10b981'],
              borderWidth: 0,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'bottom' },
            },
          },
        });
      }

      if (notificationList) {
        const items = data.notificaciones || [];
        if (!items.length) {
          notificationList.innerHTML = '<div class="text-muted">Sin notificaciones recientes todavía.</div>';
          return;
        }

        notificationList.innerHTML = items.map((item) => `
          <div class="notification-item">
            <div class="notification-title">Trámite #${item.id} - ${item.nombre_ciudadano}</div>
            <div class="small text-muted mb-1">${item.fecha_actualizacion || ''}</div>
            <div>${item.notificacion}</div>
            <span class="priority-badge status-${String(item.estado).replace(/\s+/g, '-').toLowerCase()}">${item.estado}</span>
          </div>
        `).join('');
      }
    })
    .catch(() => {
      const notificationList = document.getElementById('notificationList');
      if (notificationList) {
        notificationList.innerHTML = '<div class="text-danger">No fue posible cargar el dashboard.</div>';
      }
    });
});