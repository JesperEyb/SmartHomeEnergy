// SmartHomeEnergy Custom Card
class SmartHomeEnergyCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  setConfig(config) {
    this._config = config;
  }

  render() {
    if (!this._hass) return;

    const statusEntity = this._hass.states['sensor.smarthomeenergy_status'];
    const actionEntity = this._hass.states['sensor.smarthomeenergy_handling'];
    const planEntity = this._hass.states['sensor.smarthomeenergy_dagsplan'];
    const benefitEntity = this._hass.states['sensor.smarthomeenergy_forventet_gevinst'];
    const nextEntity = this._hass.states['sensor.smarthomeenergy_naeste_handling'];

    const status = statusEntity?.state || 'Ukendt';
    const action = actionEntity?.state || 'Idle';
    const planSummary = planEntity?.state || 'Ingen plan';
    const benefit = benefitEntity?.state || '0';
    const nextAction = nextEntity?.state || 'Ingen';

    const chargeHours = planEntity?.attributes?.charge_hours || [];
    const dischargeHours = planEntity?.attributes?.discharge_hours || [];
    const currentHour = new Date().getHours();
    const hourlyData = planEntity?.attributes?.hourly_summary || [];

    // Create hour grid
    let hourGrid = '';
    for (let i = 0; i < 24; i++) {
      const hourData = hourlyData.find(h => h.h === i) || { a: 'i' };
      const actionChar = hourData.a || 'i';
      let className = 'hour idle';
      let bgColor = '#444';

      if (actionChar === 'c') {
        className = 'hour charge';
        bgColor = '#4CAF50';
      } else if (actionChar === 'd') {
        className = 'hour discharge';
        bgColor = '#FF9800';
      }

      if (i === currentHour) {
        className += ' current';
      }

      hourGrid += `<div class="${className}" style="background:${bgColor}" title="Kl. ${i}:00 - ${actionChar === 'c' ? 'Opladning' : actionChar === 'd' ? 'Afladning' : 'Idle'}">${i}</div>`;
    }

    this.innerHTML = `
      <ha-card header="SmartHomeEnergy">
        <div class="card-content">
          <style>
            .she-container { padding: 16px; }
            .she-status-row { display: flex; justify-content: space-between; margin-bottom: 16px; }
            .she-status-item { text-align: center; flex: 1; }
            .she-status-label { font-size: 12px; color: var(--secondary-text-color); }
            .she-status-value { font-size: 18px; font-weight: bold; }
            .she-hour-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 4px; margin-top: 16px; }
            .hour {
              padding: 8px 4px;
              text-align: center;
              border-radius: 4px;
              color: white;
              font-size: 12px;
              font-weight: bold;
            }
            .hour.current { box-shadow: 0 0 0 2px white, 0 0 0 4px #2196F3; }
            .hour.charge { background: #4CAF50 !important; }
            .hour.discharge { background: #FF9800 !important; }
            .hour.idle { background: #444 !important; }
            .she-legend { display: flex; gap: 16px; margin-top: 12px; justify-content: center; }
            .she-legend-item { display: flex; align-items: center; gap: 4px; font-size: 12px; }
            .she-legend-color { width: 16px; height: 16px; border-radius: 3px; }
            .she-benefit {
              text-align: center;
              margin-top: 16px;
              padding: 12px;
              background: var(--primary-background-color);
              border-radius: 8px;
            }
            .she-benefit-value { font-size: 24px; font-weight: bold; color: #4CAF50; }
            .she-benefit-label { font-size: 12px; color: var(--secondary-text-color); }
            .she-button {
              display: block;
              width: 100%;
              padding: 12px;
              margin-top: 16px;
              background: var(--primary-color);
              color: white;
              border: none;
              border-radius: 8px;
              cursor: pointer;
              font-size: 14px;
            }
            .she-button:hover { opacity: 0.9; }
          </style>

          <div class="she-container">
            <div class="she-status-row">
              <div class="she-status-item">
                <div class="she-status-label">Status</div>
                <div class="she-status-value">${status}</div>
              </div>
              <div class="she-status-item">
                <div class="she-status-label">Handling</div>
                <div class="she-status-value">${action}</div>
              </div>
              <div class="she-status-item">
                <div class="she-status-label">Næste</div>
                <div class="she-status-value">${nextAction}</div>
              </div>
            </div>

            <div class="she-hour-grid">
              ${hourGrid}
            </div>

            <div class="she-legend">
              <div class="she-legend-item">
                <div class="she-legend-color" style="background:#4CAF50"></div>
                <span>Opladning</span>
              </div>
              <div class="she-legend-item">
                <div class="she-legend-color" style="background:#FF9800"></div>
                <span>Afladning</span>
              </div>
              <div class="she-legend-item">
                <div class="she-legend-color" style="background:#444"></div>
                <span>Idle</span>
              </div>
            </div>

            <div class="she-benefit">
              <div class="she-benefit-value">${benefit} DKK</div>
              <div class="she-benefit-label">Forventet gevinst i dag</div>
            </div>

            <button class="she-button" id="optimize-btn">
              🔄 Kør Optimering
            </button>
          </div>
        </div>
      </ha-card>
    `;

    // Add click handler for optimize button
    this.querySelector('#optimize-btn').addEventListener('click', () => {
      this._hass.callService('smarthomeenergy', 'optimize', {});
    });
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig() {
    return {};
  }
}

customElements.define('smarthomeenergy-card', SmartHomeEnergyCard);

// Register card in HACS/custom cards
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'smarthomeenergy-card',
  name: 'SmartHomeEnergy Card',
  description: 'Vis SmartHomeEnergy batteristyring status og plan',
});
