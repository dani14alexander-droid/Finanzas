const chileDateParts = new Intl.DateTimeFormat("en-CA", {
  day: "2-digit",
  month: "2-digit",
  timeZone: "America/Santiago",
  year: "numeric",
}).formatToParts(new Date());
const chileDate = Object.fromEntries(
  chileDateParts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value])
);
const todayInChile = `${chileDate.year}-${chileDate.month}-${chileDate.day}`;

document.querySelectorAll('input[type="date"]').forEach((dateInput) => {
  if (!dateInput.value) {
    dateInput.value = todayInChile;
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
  const categoryPicker = document.createElement("select");
  categoryPicker.className = "category-picker";
  categoryPicker.setAttribute("aria-label", "Categorias sugeridas");

  const refreshCategoryPicker = (filterText = "") => {
    const listId = typeSelect
      ? categoryListsByType[typeSelect.value] || "categorias-todas"
      : categoryInput.getAttribute("list") || "categorias-todas";
    const dataList = document.getElementById(listId);
    const normalizedFilter = filterText.trim().toLocaleLowerCase("es");
    const categories = Array.from(dataList?.options || [])
      .map((option) => option.value)
      .filter((category) => category.toLocaleLowerCase("es").startsWith(normalizedFilter));

    categoryPicker.replaceChildren();
    const prompt = document.createElement("option");
    prompt.value = "";
    prompt.textContent = "Selecciona una categoria";
    categoryPicker.append(prompt);
    categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      option.selected = categoryInput.value === category;
      categoryPicker.append(option);
    });

    const exactCategory = categories.find(
      (category) => category.toLocaleLowerCase("es") === normalizedFilter
    );
    if (exactCategory) {
      categoryPicker.value = exactCategory;
    } else if (normalizedFilter && categories.length) {
      categoryPicker.value = categories[0];
    }

    categoryInput.setAttribute("list", listId);
  };

  const updateCategoryList = () => {
    refreshCategoryPicker(categoryInput.value);
  };

  categoryInput.before(categoryPicker);
  categoryInput.placeholder = "O escribe otra categoria";
  refreshCategoryPicker();

  categoryPicker.addEventListener("change", () => {
    if (categoryPicker.value) {
      categoryInput.value = categoryPicker.value;
    }
  });
  categoryInput.addEventListener("input", () => {
    refreshCategoryPicker(categoryInput.value);
  });
  categoryInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && categoryPicker.value) {
      event.preventDefault();
      categoryInput.value = categoryPicker.value;
      refreshCategoryPicker(categoryInput.value);
    }
  });
  typeSelect?.addEventListener("change", updateCategoryList);
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
  const openRow = button.closest(".movement-table-wrap")?.querySelector(".inline-add-row");
  if (openRow && !openRow.hidden) {
    openRow.querySelector('[name="categoria"]')?.focus();
  }
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

document.querySelectorAll("[data-confirm-delete]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("¿Eliminar esta deuda definitivamente?")) {
      event.preventDefault();
    }
  });
});

document.querySelectorAll("[data-debt-form]").forEach((form) => {
  const type = form.elements.namedItem("tipo");
  const mode = form.elements.namedItem("modalidad");
  const modeField = form.querySelector("[data-debt-mode]");
  const installmentsField = form.querySelector("[data-installments]");
  const category = form.elements.namedItem("categoria");
  const categoryPicker = form.querySelector(".category-picker");
  const sharedExpenseField = form.querySelector("[data-shared-expense]");
  const sharedExpenseSelect = form.elements.namedItem("gasto_asociado_id");

  const updateDebtFields = () => {
    const isPayable = type.value === "Debo";
    const hasInstallments = isPayable && mode.value === "Cuotas";
    modeField.hidden = !isPayable;
    installmentsField.hidden = !hasInstallments;
    const isSharedExpense =
      type.value === "Me deben" &&
      category.value.trim().toLocaleLowerCase("es") === "compra compartida";
    if (sharedExpenseField) {
      sharedExpenseField.hidden = !isSharedExpense;
    }
    if (sharedExpenseSelect) {
      sharedExpenseSelect.disabled = !isSharedExpense;
    }
  };

  type.addEventListener("change", updateDebtFields);
  mode.addEventListener("change", updateDebtFields);
  category?.addEventListener("input", updateDebtFields);
  categoryPicker?.addEventListener("change", updateDebtFields);
  updateDebtFields();
});

document.querySelectorAll(".cash-breakdown").forEach((breakdown) => {
  const form = breakdown.closest("form");
  const list = breakdown.querySelector("[data-cash-breakdown-list]");
  const template = breakdown.querySelector("[data-cash-breakdown-template]");
  const addButton = breakdown.querySelector("[data-add-cash]");
  const mainDate = form?.elements?.namedItem("fecha");
  const type = form?.elements?.namedItem("tipo");
  const category = form?.elements?.namedItem("categoria");
  const categoryPicker = form?.querySelector(".category-picker");
  const detailTitle = breakdown.querySelector("[data-detail-title]");
  const detailHelp = breakdown.querySelector("[data-detail-help]");

  const updateCashVisibility = () => {
    const normalizedCategory = category?.value.trim().toLocaleLowerCase("es");
    const isCashExpense =
      type?.value === "Gasto" &&
      normalizedCategory === "efectivo";
    const isFlexibleSaving =
      type?.value === "Ahorro" && normalizedCategory === "ahorro flexible";
    const isDetailedMovement = isCashExpense || isFlexibleSaving;
    breakdown.hidden = !isDetailedMovement;
    breakdown.querySelectorAll("input, button").forEach((control) => {
      control.disabled = !isDetailedMovement;
    });
    if (detailTitle) {
      detailTitle.textContent = isFlexibleSaving
        ? "Retiros del ahorro flexible"
        : "Desglose de gasto en efectivo";
    }
    if (detailHelp) {
      detailHelp.textContent = isFlexibleSaving
        ? "Registra aquí cada retiro y su destino. La suma no puede superar el ahorro."
        : "La suma del detalle no puede superar el monto total.";
    }
  };

  const setDefaultDate = (row) => {
    const dateInput = row.querySelector('input[name="sub_fecha"]');
    if (dateInput && !dateInput.value) {
      dateInput.value = mainDate?.value || "";
    }
  };

  addButton?.addEventListener("click", () => {
    const row = template.content.firstElementChild.cloneNode(true);
    setDefaultDate(row);
    list.append(row);
    row.querySelector('input[name="sub_categoria"]')?.focus();
  });

  list?.addEventListener("click", (event) => {
    const removeButton = event.target.closest("[data-remove-cash]");
    if (!removeButton) {
      return;
    }
    const rows = list.querySelectorAll(".cash-breakdown-row");
    const row = removeButton.closest(".cash-breakdown-row");
    if (rows.length > 1) {
      row.remove();
      return;
    }
    row.querySelectorAll("input").forEach((input) => {
      input.value = input.name === "sub_fecha" ? mainDate?.value || "" : "";
    });
  });

  type?.addEventListener("change", updateCashVisibility);
  category?.addEventListener("input", updateCashVisibility);
  categoryPicker?.addEventListener("change", updateCashVisibility);
  updateCashVisibility();
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

const buildAvailableHistory = () => {
  const canvas = document.getElementById("disponibleHistoricoChart");
  const data = readChartData("disponible-history-data");
  if (!canvas || !data || !window.Chart) {
    return;
  }

  new Chart(canvas, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [{
        label: "Dinero disponible",
        data: data.values,
        borderColor: "#1f6feb",
        backgroundColor: "rgba(31, 111, 235, 0.12)",
        fill: true,
        pointBackgroundColor: "#1f6feb",
        pointRadius: 3,
        tension: 0.25,
      }],
    },
    options: {
      maintainAspectRatio: false,
      responsive: true,
      plugins: {
        datalabels: { display: false },
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            label: (context) => `Disponible: ${moneyFormatter.format(Number(context.raw || 0))}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: "#667085", maxRotation: 0 } },
        y: {
          grid: { color: "#d9e0ea" },
          ticks: {
            callback: (value) => moneyFormatter.format(value),
            color: "#667085",
            maxTicksLimit: 5,
          },
        },
      },
    },
    plugins: window.ChartDataLabels ? [ChartDataLabels] : [],
  });
};

buildAvailableHistory();

const buildVariableExpensesChart = () => {
  const canvas = document.getElementById("gastosVariablesChart");
  const data = readChartData("variable-expenses-data");
  if (!canvas || !data || !window.Chart) {
    return;
  }

  const goal = Number(data.goal || 0);
  const values = data.values.map((value) => Number(value || 0));
  const detailPanel = document.getElementById("variable-expenses-detail");
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
  const renderVariableDetail = (index) => {
    if (!detailPanel || !data.details?.[index]) {
      return;
    }
    const detail = data.details[index];
    const categories = detail.categorias.length
      ? detail.categorias.map((item) => `
          <li><span>${escapeHtml(item.categoria)}</span><strong>${moneyFormatter.format(item.monto)}</strong></li>
        `).join("")
      : "<li><span>Sin gastos</span><strong>$0</strong></li>";
    const purchases = detail.detalles.length
      ? detail.detalles.map((item) => `
          <tr>
            <td>${escapeHtml(item.fecha)}</td>
            <td>${escapeHtml(item.descripcion)}</td>
            <td>${escapeHtml(item.categoria)}</td>
            <td>${moneyFormatter.format(item.monto)}</td>
          </tr>
        `).join("")
      : '<tr><td colspan="4">No hubo gastos variables en este periodo.</td></tr>';
    detailPanel.innerHTML = `
      <div class="variable-detail-header">
        <div><span>Desglose</span><h3>${escapeHtml(detail.etiqueta)}</h3></div>
        <strong>${moneyFormatter.format(detail.monto)}</strong>
      </div>
      <div class="variable-category-summary">
        <h4>Resumen por categoría</h4>
        <ul>${categories}</ul>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Fecha</th><th>Compra</th><th>Categoría</th><th>Valor</th></tr></thead>
          <tbody>${purchases}</tbody>
        </table>
      </div>
    `;
    detailPanel.hidden = false;
    detailPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "Gasto variable",
          data: values,
          backgroundColor: values.map((value) => value > goal ? "#1f6feb" : "#7dd3fc"),
          borderColor: values.map((value) => value > goal ? "#1d4ed8" : "#38bdf8"),
          borderRadius: 5,
          borderWidth: 1,
          order: 2,
        },
        {
          type: "line",
          label: "Meta",
          data: data.labels.map(() => goal),
          borderColor: "#dc2626",
          borderDash: [8, 6],
          borderWidth: 2,
          pointRadius: 0,
          tension: 0,
          order: 1,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      responsive: true,
      interaction: { intersect: false, mode: "index" },
      onClick: (_event, elements) => {
        const bar = elements.find((element) => element.datasetIndex === 0);
        if (bar) {
          renderVariableDetail(bar.index);
        }
      },
      onHover: (event, elements) => {
        if (event.native?.target) {
          event.native.target.style.cursor = elements.some((element) => element.datasetIndex === 0)
            ? "pointer"
            : "default";
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => {
              const value = Number(context.raw || 0);
              if (context.dataset.type === "line") {
                return `Meta: ${moneyFormatter.format(value)}`;
              }
              const difference = value - goal;
              const comparison = difference > 0
                ? `Sobre la meta por ${moneyFormatter.format(difference)}`
                : difference < 0
                  ? `Bajo la meta por ${moneyFormatter.format(Math.abs(difference))}`
                  : "Exactamente en la meta";
              return [`Gasto: ${moneyFormatter.format(value)}`, comparison];
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#667085", maxRotation: data.view === "diaria" ? 45 : 0 },
        },
        y: {
          beginAtZero: true,
          grid: { color: "#d9e0ea" },
          ticks: {
            callback: (value) => moneyFormatter.format(value),
            color: "#667085",
            maxTicksLimit: 6,
          },
        },
      },
    },
  });
};

buildVariableExpensesChart();
