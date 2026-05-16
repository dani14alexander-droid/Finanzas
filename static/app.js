document.querySelectorAll('input[type="date"]').forEach((dateInput) => {
  if (!dateInput.value) {
    dateInput.valueAsDate = new Date();
  }
});

const categoryListsByType = {
  Ahorro: "categorias-ahorro",
  Debo: "categorias-debo",
  Gasto: "categorias-gasto",
  Ingreso: "categorias-ingreso",
  "Me deben": "categorias-me-deben",
};

document.querySelectorAll("[data-category-list]").forEach((categoryInput) => {
  const form = categoryInput.form || categoryInput.closest("form");
  const typeSelect = form?.elements?.namedItem("tipo");
  if (!typeSelect) {
    return;
  }

  const updateCategoryList = () => {
    categoryInput.setAttribute(
      "list",
      categoryListsByType[typeSelect.value] || "categorias-todas"
    );
  };

  updateCategoryList();
  typeSelect.addEventListener("change", updateCategoryList);
});

document.querySelectorAll(".auto-filter").forEach((form) => {
  const search = form.querySelector('input[type="search"]');
  const select = form.querySelector("select");

  if (search) {
    search.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        form.requestSubmit();
      }
    });
  }

  if (select) {
    select.addEventListener("change", () => form.requestSubmit());
  }
});

document.querySelectorAll(".add-row-button").forEach((button) => {
  button.addEventListener("click", () => {
    const wrap = button.closest(".movement-table-wrap");
    const row = wrap?.querySelector(".inline-add-row");
    if (!row) {
      return;
    }

    row.hidden = !row.hidden;
    if (!row.hidden) {
      row.querySelector("input, select")?.focus();
    }
  });
});

document.querySelectorAll("[data-open-dialog]").forEach((button) => {
  button.addEventListener("click", () => {
    const dialog = document.getElementById(button.dataset.openDialog);
    if (!dialog) {
      return;
    }

    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    dialog.querySelector("input")?.focus();
  });
});

document.querySelectorAll("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => {
    button.closest("dialog")?.close();
  });
});

document.querySelectorAll(".reason-dialog").forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });
});

document.querySelectorAll(".history-chart .bar").forEach((bar) => {
  const showDetail = () => {
    const panel = bar.closest(".panel");
    const detail = panel?.querySelector(".bar-detail");
    if (!detail || !bar.dataset.detail) {
      return;
    }

    panel.querySelectorAll(".bar.active").forEach((item) => item.classList.remove("active"));
    bar.classList.add("active");

    const data = JSON.parse(bar.dataset.detail);
    const rows = data.items.length
      ? data.items
          .map(
            (item) => `
              <li>
                <span>${item.fecha}</span>
                <strong>${item.nombre}</strong>
                <b>${item.monto}</b>
              </li>
            `
          )
          .join("")
      : "<li><span>-</span><strong>Sin operaciones</strong><b>$0</b></li>";

    detail.innerHTML = `
      <h2>${data.titulo}</h2>
      <p class="detail-total">Total: ${data.total}</p>
      <ul>${rows}</ul>
    `;
    detail.hidden = false;
  };

  bar.addEventListener("click", showDetail);
  bar.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      showDetail();
    }
  });
});

const moneyFormatter = new Intl.NumberFormat("es-CL", {
  currency: "CLP",
  maximumFractionDigits: 0,
  style: "currency",
});

const readChartData = (id) => {
  const node = document.getElementById(id);
  if (!node) {
    return null;
  }
  return JSON.parse(node.textContent);
};

const buildDoughnut = (canvasId, dataId) => {
  const canvas = document.getElementById(canvasId);
  const data = readChartData(dataId);
  if (!canvas || !data || !window.Chart || !window.ChartDataLabels) {
    return;
  }

  const total = data.values.reduce((sum, value) => sum + Number(value || 0), 0);
  Chart.register(ChartDataLabels);

  new Chart(canvas, {
    data: {
      datasets: [
        {
          backgroundColor: data.colors,
          borderColor: "#f8fafc",
          borderWidth: 2,
          data: data.values,
          hoverOffset: 6,
        },
      ],
      labels: data.labels,
    },
    options: {
      cutout: "58%",
      plugins: {
        datalabels: {
          color: "#ffffff",
          display: (context) => {
            const value = Number(context.dataset.data[context.dataIndex] || 0);
            return total > 0 && value / total >= 0.07;
          },
          font: {
            size: 13,
            weight: "800",
          },
          formatter: (value) => `${Math.round((Number(value || 0) / total) * 100)}%`,
          textStrokeColor: "rgba(0, 0, 0, 0.45)",
          textStrokeWidth: 3,
        },
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const value = Number(context.raw || 0);
              const pct = total ? Math.round((value / total) * 100) : 0;
              return `${context.label}: ${moneyFormatter.format(value)} (${pct}%)`;
            },
          },
        },
      },
      responsive: false,
    },
    type: "doughnut",
  });
};

buildDoughnut("gastosChart", "gastos-chart-data");
buildDoughnut("ingresosChart", "ingresos-chart-data");

const renderDetailPanel = (panel, data) => {
  const rows = data.items.length
    ? data.items
        .map(
          (item) => `
            <li>
              <span>${item.fecha}</span>
              <strong>${item.nombre}</strong>
              <b>${item.monto}</b>
            </li>
          `
        )
        .join("")
    : "<li><span>-</span><strong>Sin operaciones</strong><b>$0</b></li>";

  panel.innerHTML = `
    <h2>${data.titulo}</h2>
    <p class="detail-total">Total: ${data.total}</p>
    <ul>${rows}</ul>
  `;
  panel.hidden = false;
};

const buildHistoryBar = (canvasId, dataId) => {
  const canvas = document.getElementById(canvasId);
  const data = readChartData(dataId);
  if (!canvas || !data || !window.Chart) {
    return;
  }

  new Chart(canvas, {
    data: {
      datasets: data.datasets.map((dataset) => ({
        backgroundColor: dataset.color,
        borderRadius: 4,
        data: dataset.values,
        label: dataset.label,
      })),
      labels: data.labels,
    },
    options: {
      maintainAspectRatio: false,
      onClick: (event, elements, chart) => {
        if (!elements.length) {
          return;
        }
        const point = elements[0];
        const raw = data.datasets[point.datasetIndex].details[point.index];
        const detail = typeof raw === "string" ? JSON.parse(raw) : raw;
        const panel = canvas.closest(".panel")?.querySelector(".bar-detail");
        if (panel) {
          renderDetailPanel(panel, detail);
        }
      },
      plugins: {
        datalabels: {
          display: false,
        },
        legend: {
          labels: {
            boxHeight: 10,
            boxWidth: 10,
            color: "#667085",
            font: {
              weight: "700",
            },
            usePointStyle: true,
          },
          position: "bottom",
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const value = Number(context.raw || 0);
              return `${context.dataset.label}: ${moneyFormatter.format(value)}`;
            },
          },
        },
      },
      responsive: true,
      scales: {
        x: {
          grid: {
            display: false,
          },
          ticks: {
            color: "#667085",
            maxRotation: 0,
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: "#d9e0ea",
          },
          ticks: {
            callback: (value) => moneyFormatter.format(value),
            color: "#667085",
            maxTicksLimit: 5,
          },
        },
      },
    },
    plugins: window.ChartDataLabels ? [ChartDataLabels] : [],
    type: "bar",
  });
};

buildHistoryBar("movimientosHistoricoChart", "movimientos-history-data");
buildHistoryBar("deudasHistoricoChart", "deudas-history-data");
