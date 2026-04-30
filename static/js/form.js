// FJS-12 — Patient info form: dynamic field visibility based on
// procedure_type (knee | hip | osseointegration | socket_prosthesis)
// and side (right | left | bilateral).
//
// Key trick: hidden field groups have all their <select>s set to disabled,
// so they are NOT submitted with the form. This prevents conflicts between
// duplicate-name selects (e.g. amputation_year_right used by both osseo and
// socket flows) and avoids "required" errors on hidden inputs.

(function () {
    'use strict';

    const form = document.getElementById('patientForm');
    if (!form) return;

    const procedureRadios = form.querySelectorAll('input[name="procedure_type"]');
    const sideRadios = form.querySelectorAll('input[name="side"]');
    const sideBlocks = form.querySelectorAll('.side-block');

    function getProcedure() {
        const checked = form.querySelector('input[name="procedure_type"]:checked');
        return checked ? checked.value : null;
    }

    function getSide() {
        const checked = form.querySelector('input[name="side"]:checked');
        return checked ? checked.value : null;
    }

    /**
     * For each field group inside a side block, decide whether it should be
     * active (visible & submitted) based on the procedure type. Disable selects
     * inside inactive groups so they don't pollute the form data.
     */
    function configureBlock(block, sideVisible, procedure) {
        if (!block) return;

        block.classList.toggle('visible', sideVisible);

        // Reset procedure-specific classes on the block
        block.classList.remove('proc-knee', 'proc-hip', 'proc-osseo', 'proc-socket');
        if (sideVisible && procedure) {
            const procClassMap = {
                'knee': 'proc-knee',
                'hip': 'proc-hip',
                'osseointegration': 'proc-osseo',
                'socket_prosthesis': 'proc-socket',
            };
            const cls = procClassMap[procedure];
            if (cls) block.classList.add(cls);
        }

        // Decide which field groups are active for this procedure
        const isKneeOrHip = procedure === 'knee' || procedure === 'hip';
        const isOsseo = procedure === 'osseointegration';
        const isSocket = procedure === 'socket_prosthesis';

        const activeMap = {
            '.surgery-date-field':    sideVisible && (isKneeOrHip || isOsseo),
            '.amputation-date-field': sideVisible && isSocket,
            '.amputation-year-field': sideVisible && isOsseo,
            '.amputation-level-field': sideVisible && (isOsseo || isSocket),
        };

        Object.keys(activeMap).forEach(selector => {
            const group = block.querySelector(selector);
            if (!group) return;
            const active = activeMap[selector];
            // Toggle active class for CSS visibility
            group.classList.toggle('active', active);
            // Enable/disable selects inside; required if active
            group.querySelectorAll('select, input').forEach(f => {
                f.disabled = !active;
                f.required = active;
            });
        });
    }

    function update() {
        const procedure = getProcedure();
        const side = getSide();
        const showRight = side === 'right' || side === 'bilateral';
        const showLeft = side === 'left' || side === 'bilateral';

        sideBlocks.forEach(block => {
            const blockSide = block.dataset.side;
            const visible = (blockSide === 'right' && showRight) ||
                            (blockSide === 'left'  && showLeft);
            configureBlock(block, visible, procedure);
        });
    }

    procedureRadios.forEach(r => r.addEventListener('change', update));
    sideRadios.forEach(r => r.addEventListener('change', update));

    // Run once on load (handles prefilled state after server-side validation error)
    update();
})();
