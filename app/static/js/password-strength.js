(() => {
  const wrappers = document.querySelectorAll('[data-password-strength]');

  wrappers.forEach(wrapper => {
    const form = wrapper.closest('form');
    if (!form) return;

    const input = form.querySelector('input[name="password"]');
    if (!input) return;

    const fill = wrapper.querySelector('.strength-fill');
    const label = wrapper.querySelector('.strength-label strong');
    const scoreEl = wrapper.querySelector('.strength-score');

    const rules = {
      length: wrapper.querySelector('[data-rule="length"]'),
      upper: wrapper.querySelector('[data-rule="upper"]'),
      lower: wrapper.querySelector('[data-rule="lower"]'),
      number: wrapper.querySelector('[data-rule="number"]'),
      special: wrapper.querySelector('[data-rule="special"]')
    };

    const labels = ['Muito fraca', 'Fraca', 'Regular', 'Boa', 'Forte', 'Muito forte'];
    const classes = ['s0', 's1', 's2', 's3', 's4', 's5'];

    function evaluate(value) {
      const checks = {
        length: value.length >= 10,
        upper: /[A-Z]/.test(value),
        lower: /[a-z]/.test(value),
        number: /\d/.test(value),
        special: /[^A-Za-z0-9]/.test(value)
      };

      let score = Object.values(checks).filter(Boolean).length;

      Object.entries(checks).forEach(([key, ok]) => {
        if (rules[key]) rules[key].classList.toggle('ok', ok);
      });

      fill.className = 'strength-fill ' + classes[score];
      fill.style.width = `${score * 20}%`;
      label.textContent = labels[score];
      scoreEl.textContent = `${score}/5`;

      wrapper.classList.toggle('complete', score === 5);
    }

    input.addEventListener('input', () => evaluate(input.value));
    evaluate(input.value);
  });
})();
