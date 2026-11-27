# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The analysis gestures of one IMASViz session: events, spectra, physics cuts and campaigns.

Detect events on one curve, report the spectrum and cross-correlate two, the physics cuts of a campaign, and the HTML reports of each. Everything is read off the same curves the figures draw.
"""

from imasviz.VizAgent.core import EVENT_MARKER_CAP, _REPORT_CSS

class AnalysisOps:
    """The physics: events, spectra, cuts and campaigns, with their reports."""

    def _readSignalForEvents(self, uri, path, along, indices):
        """The two axes an event is read on: what get_signal answers for the
        leaf, one array at a time. A leaf the read answers as more than one
        array is refused by name, because one event kind is read on one axis
        -- the value a figure of the same leaf draws, so detection and the
        plot are the same read."""
        payload = self.get_signal(
            uri, path, along=along,
            indices=None if indices is None else indices)
        if not isinstance(payload, dict) or payload.get('kind') != 'curve':
            kind = payload.get('kind') if isinstance(payload, dict) \
                else type(payload).__name__
            raise ValueError(
                'The leaf "%s" answers %r: an event is read on the one '
                'axis the read gives (name it with `along` and `indices`), '
                'not on a multi-array answer.' % (path, kind))
        x = payload.get('x')
        y = payload.get('y')
        if x is None or y is None:
            raise ValueError(
                'The read of "%s" answered but has no x and y an event can '
                'be read off: name the axis it runs on, or the element it '
                'is fixed on.' % path)
        return x, y

    def _readCurveSignal(self, uri, path, along, indices):
        """The two axes the leaf answers as a curve, one array at a time.

        The generic read the event detection, the spectrum and the
        cross-correlation all run on -- the value a figure of the same leaf
        draws, so the analysis and the plot are one read. `_readSignalForEvents`
        is that same read, kept under the earlier name."""
        return self._readSignalForEvents(uri, path, along, indices)

    def _addEventMarkers(self, frame, figure_key, block):
        """The event marks on a curve figure: one vertical per event, capped.

        A mark is a pyqtgraph InfiniteLine on the abscissa the curve runs
        along; the frame holds the set so clear_event_marks takes them off.
        More than the cap is refused by name, because dozens of lines are a
        wall across the curve, and the report is the shape that many events
        want.
        """
        import pyqtgraph as pg

        events = block['events']
        if len(events) > EVENT_MARKER_CAP:
            raise ValueError(
                'The signal holds %d %s event(s): a figure carries at most '
                '%d marks, and past that the lines are a wall -- the report '
                'is the shape that many want.'
                % (len(events), block['kind'], EVENT_MARKER_CAP))
        plot = getattr(frame, 'pgPlotWidget', None)
        if plot is None or not hasattr(plot, 'addItem'):
            raise ValueError(
                'The window "%s" is not a curve figure: a mark sits on the '
                'axis a curve was drawn along, so name the figure a curve '
                'was drawn in.' % figure_key)
        pen = pg.mkPen((255, 122, 40), width=2)
        markers = []
        for event in events:
            line = pg.InfiniteLine(pos=float(event['t']), angle=90,
                                   pen=pen, movable=False)
            plot.addItem(line)
            markers.append(line)
        frame._eventMarkers = markers
        return len(markers)

    def detect_events(self, uri, path, kind, threshold=None,
                      prominence=None, min_distance=None, direction=None,
                      hysteresis=None, along=None, indices=None,
                      figure_key=None):
        """The events of one kind, read off the leaf's signal.

        `kind` `'elm'` (an excursion up), `'sawtooth'` (a crash down), or
        `'lh'` (a threshold crossing). The signal is the one `get_signal`
        answers for the leaf -- the value a figure of the same leaf draws --
        so what is detected and what is plotted are the same read. `threshold`
        / `prominence` / `min_distance` gate an ELM or a sawtooth;
        `threshold` / `direction` / `hysteresis` gate an L-H crossing, and a
        kind the caller did not pick refuses a parameter it does not take,
        by name. `along` and `indices` address the leaf the way `plot_one`
        and `get_signal` do, so the read is theirs.

        When `figure_key` names a curve figure, the events are marked on it
        (capped; clear_event_marks takes the marks off). A figure that is
        not a curve figure, or a leaf the read answers as more than one
        axis, is refused by name.
        """
        from imasviz.VizAnalysis.detect import detect

        x, y = self._readSignalForEvents(uri, path, along, indices)
        params = {}
        for pname, given in (('threshold', threshold),
                             ('prominence', prominence),
                             ('min_distance', min_distance),
                             ('direction', direction),
                             ('hysteresis', hysteresis)):
            if given is not None:
                params[pname] = given
        block = detect(kind, x, y, **params)
        self._logFor([uri],
                     'detect_events: %d %s event(s) read off %s (the mean '
                     'spacing is %s s).'
                     % (block['count'], block['kind'], path,
                        block['period']['period_mean']))
        answer = dict(block)
        if figure_key is not None:
            _record, frame = self._windowForKey(figure_key)
            answer['figure'] = figure_key
            answer['markers'] = self._addEventMarkers(frame, figure_key,
                                                       block)
        return answer

    def clear_event_marks(self, figure_key):
        """The event marks off a curve figure, one the detect_events put there.

        Safe to call when the figure holds no marks: it answers the number
        it took off, which is zero in that case. A figure that is not in the
        session is refused the way the rest of the window gestures refuse.
        """
        record, frame = self._windowForKey(figure_key)
        markers = list(getattr(frame, '_eventMarkers', None) or [])
        plot = getattr(frame, 'pgPlotWidget', None)
        if plot is not None:
            for line in markers:
                try:
                    plot.removeItem(line)
                except Exception:
                    pass
        frame._eventMarkers = []
        self._logFor(record.cases,
                     'clear_event_marks: %d mark(s) off %s.'
                     % (len(markers), figure_key))
        return {'figure': figure_key, 'cleared': len(markers)}

    def events_report(self, uri, path, kind, threshold=None,
                      prominence=None, min_distance=None, direction=None,
                      hysteresis=None, along=None, indices=None,
                      figure_key=None, name=None):
        """The events of one kind as a self-contained HTML report.

        The same read and the same detection detect_events uses -- nothing is
        detected from memory -- with the events in their own table, the
        period of their times, and the figure when one is named (the picture
        of it). The file lands under `~/.imasviz/reports` like the other
        reports, and a name that names a place, not a report, is refused by
        name.
        """
        from imasviz.VizAnalysis.detect import detect

        x, y = self._readSignalForEvents(uri, path, along, indices)
        params = {}
        for pname, given in (('threshold', threshold),
                             ('prominence', prominence),
                             ('min_distance', min_distance),
                             ('direction', direction),
                             ('hysteresis', hysteresis)):
            if given is not None:
                params[pname] = given
        block = detect(kind, x, y, **params)

        image = None
        if figure_key is not None:
            try:
                image = self.screenshot(figure_key)
            except ValueError:
                image = None

        out = self._namedReport(name, block['count'])
        self._writeEventReport(out, kind=kind, uri=uri, leaf=path,
                               block=block, image=image)
        cases = [uri] + ([figure_key] if figure_key is not None else [])
        self._logFor(cases,
                     'events_report wrote %s: %d %s event(s) read off %s.'
                     % (out, block['count'], block['kind'], path))
        return {'saved_to': out, 'count': block['count'],
                'kind': block['kind']}

    def _writeEventReport(self, path, kind, uri, leaf, block, image):
        """The event report's own page: the events in a table, the period of
        their times, the image when there is one, and nothing to fetch --
        the shape the other reports keep, in the same little style."""
        import base64
        import html

        period = block['period']

        if kind in ('lh', 'l_h', 'mode', 'transition'):
            header = ('<tr><th>#</th><th>time</th><th>value</th>'
                      '<th>direction</th></tr>')

            def row(i, event):
                return (
                    '<tr><td class="s">%d</td><td class="s">%s</td>'
                    '<td class="s">%s</td><td class="s">%s</td></tr>'
                    % (i, self._num(event['t']), self._num(event['value']),
                       html.escape(str(event.get('direction', '')))))
        else:
            header = ('<tr><th>#</th><th>time</th><th>value</th>'
                      '<th>prominence</th></tr>')

            def row(i, event):
                return (
                    '<tr><td class="s">%d</td><td class="s">%s</td>'
                    '<td class="s">%s</td><td class="s">%s</td></tr>'
                    % (i, self._num(event['t']), self._num(event['value']),
                       self._num(event.get('prominence'))))

        def show(value):
            if value is None:
                return '—'
            return ('%g' % float(value)) if isinstance(value, float) \
                else str(value)

        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape('%s events' % kind), _REPORT_CSS),
            '<h1>%s</h1>' % html.escape('%s events read off %s' % (kind, leaf)),
            '<p class="sub">%s — %d event(s) · mean spacing %s s</p>' % (
                html.escape(uri), block['count'],
                show(period['period_mean'])),
        ]
        if image:
            parts.append(
                '<img alt="%s events" src="data:image/png;base64,%s">' % (
                    html.escape(kind),
                    base64.b64encode(image).decode('ascii')))
        parts.append('<table>')
        parts.append(header)
        for i, event in enumerate(block['events']):
            parts.append(row(i, event))
        parts.append('</table>')
        parts.append(
            '<p class="sub">count %d · span %s · mean %s · min %s · '
            'max %s · rate %s Hz</p>'
            % (block['count'], show(period['span']),
               show(period['period_mean']), show(period['period_min']),
               show(period['period_max']), show(period['mean_rate_hz'])))
        parts.append('</body></html>')
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(parts))
        except OSError as error:
            raise ValueError('The report could not be written to %s: %s'
                             % (path, error))

    def spectrum(self, uri, path, n_peaks=None, band_low=None, band_high=None,
                 along=None, indices=None):
        """What the leaf's time series oscillates at, and where its power is.

        The read is the one `spectrum` is drawn from -- `get_signal`, the value
        a figure of the same leaf shows -- so the frequency read is the one the
        curve is. `n_peaks` is how many leading peaks come back (five); a band
        is two bounds, `band_low` and `band_high`, and a band asked for only one
        of them is refused by name; the share of the power in it is `band`.
        `along` and `indices` address the leaf the way `plot_one` and
        `get_signal` do.

        A flat series, or one too short to spread its power over a frequency,
        is refused the way the analysis layer says it, never a plausible-looking
        number.
        """
        from imasviz.VizAnalysis.spectra import band_power
        from imasviz.VizAnalysis.spectra import spectrum as ask

        if (band_low is None) != (band_high is None):
            present, absent = (('band_high', 'band_low')
                               if band_low is None else ('band_low', 'band_high'))
            raise ValueError(
                '%s is named with %s absent: a band is its two bounds, so name '
                'both or neither.' % (present, absent))
        x, y = self._readCurveSignal(uri, path, along, indices)
        block = ask(x, y, n_peaks=5 if n_peaks is None else int(n_peaks))
        dominant = block['dominant']
        answer = dict(block)
        if band_low is not None and band_high is not None:
            answer['band'] = band_power(x, y, band_low, band_high)
        self._logFor([uri], 'spectrum: %s reads dominant %g Hz (period %g s), '
                     '%d peak(s) answered.'
                     % (path, dominant['frequency'],
                        dominant['period'] or -1.0, len(block['peaks'])))
        return answer

    def cross_correlation(self, uri, path, path_b, along=None, indices=None,
                          indices_b=None):
        """How far `path_b` lags or leads `path`, and at what the two ring.

        Both reads are the ones a figure draws (`get_signal`, the value the two
        curves carry), so a pair the case does not hold at one length, or on two
        clocks, is refused the way the analysis says it, not a lag that would
        not mean one. The lag is in samples and in the time those samples are on
        the shared clock; the correlation is that of the peak; the shared
        frequency is the one the two agree to oscillate at.
        """
        from imasviz.VizAnalysis.spectra import cross_correlation as ask

        x, y = self._readCurveSignal(uri, path, along, indices)
        xb, yb = self._readCurveSignal(uri, path_b, along, indices_b)
        answer = ask(x, y, xb, yb)
        self._logFor([uri], 'cross_correlation: %s lags %s by %d sample(s) '
                     '(%g s), correlation %g, ringing together at %g Hz.'
                     % (path_b, path, answer['lag_samples'],
                        answer['lag_time'], answer['correlation'],
                        answer['dominant_shared_frequency']))
        return answer

    def spectrum_report(self, uri, path, n_peaks=None, band_low=None,
                        band_high=None, along=None, indices=None, figure_key=None,
                        name=None):
        """The spectral facts of a leaf's series as a self-contained HTML page.

        The same read and the same `spectrum` the facts run on -- nothing is
        read from memory -- with the leading peaks in a table, the band when one
        is named, and the picture of the figure when a curve figure is named.
        The file lands under `~/.imasviz/reports` like the other reports.
        """
        from imasviz.VizAnalysis.spectra import band_power
        from imasviz.VizAnalysis.spectra import spectrum as ask

        if (band_low is None) != (band_high is None):
            raise ValueError('a band is its two bounds, so name both or neither')
        x, y = self._readCurveSignal(uri, path, along, indices)
        block = ask(x, y, n_peaks=5 if n_peaks is None else int(n_peaks))
        band = band_power(x, y, band_low, band_high) \
            if (band_low is not None and band_high is not None) else None
        image = None
        if figure_key is not None:
            try:
                image = self.screenshot(figure_key)
            except ValueError:
                image = None
        out = self._namedReport(name, len(block['peaks']))
        self._writeSpectrumReport(out, uri=uri, leaf=path, block=block,
                                  band=band, figure_key=figure_key,
                                  image=image)
        cases = [uri] + ([figure_key] if figure_key is not None else [])
        self._logFor(cases, 'spectrum_report wrote %s: %s dominant %g Hz.'
                     % (out, path, block['dominant']['frequency']))
        return {'saved_to': out,
                'dominant_frequency': block['dominant']['frequency'],
                'peaks': len(block['peaks'])}

    def _writeSpectrumReport(self, path, uri, leaf, block, band,
                             figure_key, image):
        """The spectrum page: the leading peaks in a table, the band when there
        is one, the figure's picture when it is named, nothing to fetch -- the
        shape the other reports keep, in the same little style."""
        import base64
        import html

        def show(value):
            if value is None:
                return '—'
            return ('%g' % float(value)) if isinstance(value, float) \
                else str(value)

        dominant = block['dominant']
        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape('spectrum of %s' % leaf), _REPORT_CSS),
            '<h1>%s</h1>' % html.escape('spectrum of %s' % leaf),
            '<p class="sub">%s — dominant %s Hz (period %s s) · '
            '%d sample(s)</p>'
            % (html.escape(uri), show(dominant['frequency']),
               show(dominant['period']), block['samples']),
        ]
        if image:
            parts.append(
                '<img alt="figure" src="data:image/png;base64,%s">' %
                base64.b64encode(image).decode('ascii'))
        parts.append('<table>')
        parts.append('<tr><th>#</th><th>frequency (Hz)</th><th>period (s)</th>'
                     '<th>power</th><th>share</th></tr>')
        for i, peak in enumerate(block['peaks']):
            parts.append(
                '<tr><td class="s">%d</td><td class="s">%s</td>'
                '<td class="s">%s</td><td class="s">%s</td>'
                '<td class="s">%s</td></tr>'
                % (i, self._num(peak['frequency']), self._num(peak['period']),
                   self._num(peak['power']),
                   ('%.3f' % peak['fraction']) if peak['fraction'] is not None
                   else '—'))
        parts.append('</table>')
        foot = 'total power %s' % show(block['total_power'])
        if band is not None:
            lo, hi = band['band']
            foot += (' · band %g—%g Hz holds %.1f%% of it'
                     % (lo, hi, 100.0 * band['fraction']))
        parts.append('<p class="sub">%s</p>' % foot)
        parts.append('</body></html>')
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(parts))
        except OSError as error:
            raise ValueError('The report could not be written to %s: %s'
                             % (path, error))

    def greenwald(self, uri, n_e_path, ip_path, area_path,
                  along=None, indices=None, indices_ip=None, indices_area=None):
        """The Greenwald fraction of a case, over the time the three read.

        `f_G` = `n_e / n_G`, with the Greenwald limit the standard gives,
        `n_G = (I_pl / A) x 1e20`, `I_pl` in mega-Ampere and `A` in square
        metre, so the ratio is metre-cubed. The three reads are the ones a
        figure draws -- `get_signal`, the value the three leaves show -- so a
        case that does not hold one, or holds the three at different lengths,
        is refused the way `cross_correlation` refuses a pair it cannot hold.
        The answer is the fraction, the limit, and the three leaves, so the
        numbers a physicist checks come from the case, not from this method.
        """
        from imasviz.VizAnalysis.spectra import greenwald_fraction as ask

        ne = self._readCurveSignal(uri, n_e_path, along, indices)
        ip = self._readCurveSignal(uri, ip_path, along, indices_ip)
        area = self._readCurveSignal(uri, area_path, along, indices_area)
        answer = ask(ne[1], ip[1], area[1])
        answer['n_e_path'] = n_e_path
        answer['ip_path'] = ip_path
        answer['area_path'] = area_path
        limit = answer['greenwald_limit']
        frac = answer['greenwald_fraction']
        self._logFor([uri], 'greenwald: f_G = %g at t=%g, '
                     'n_G = %g (n_e=%s / n_G=%s x 1e20), on %d point(s).'
                     % (frac[0] if frac else -1.0,
                        ne[0][0] if ne[0] is not None and ne[0] else -1.0,
                        limit[0] if limit else -1.0,
                        n_e_path, area_path, answer['points']))
        return answer

    def _scalarCurve(self, name, uri, path, x, y):
        """The values of a curve read, with the path that named them, the stats
        finite and None-where-empty, and one log line naming the numbers."""
        y = list(y)
        finite = [v for v in y if v == v]
        answer = {
            name: y,
            'path': path,
            'points': len(y),
            'mean': (sum(finite) / len(finite)) if finite else None,
            'max': max(finite) if finite else None,
            'min': min(finite) if finite else None,
        }
        self._logFor([uri], '%s: %d point(s) read off %s; mean %s, max %s, '
                     'min %s.' % (name, len(y), path,
                                 '%g' % answer['mean'] if finite else '-',
                                 '%g' % answer['max'] if finite else '-',
                                 '%g' % answer['min'] if finite else '-'))
        return answer

    def beta_normal(self, uri, path=None, along=None, indices=None):
        """The case's normalized beta, over the time it is held.

        `path` is the leaf to read; the default is the one the equilibrium case
        keeps for it (`global_quantities.beta_normal`), but any path the case
        holds as a curve answers the same. The answer is the case's own number,
        spelled under its name, with its mean, peak and floor -- not a beta
        this method did. A case that does not hold the path is refused by name.
        """
        path = path or 'equilibrium.time_slice[0].global_quantities.beta_normal'
        x, y = self._readCurveSignal(uri, path, along, indices)
        return self._scalarCurve('beta_normal', uri, path, x, y)

    def total_pressure(self, uri, path=None, along=None, indices=None):
        """The case's total pressure p = n_e k_B T_e + n_i k_B T_i.

        `path` is the leaf to read; the default is the total (the one the
        equilibrium case keeps, `profiles_1d.pressure`) -- the case is the one
        that summed electrons and ions, and these two lines document that sum
        rather than pretend to have done it. A case that does not hold the path
        is refused by name, never a plausible-looking profile.
        """
        path = path or 'equilibrium.time_slice[0].profiles_1d.pressure'
        x, y = self._readCurveSignal(uri, path, along, indices)
        return self._scalarCurve('pressure', uri, path, x, y)

    def _shotValue(self, uri, path, at, which, along, indices):
        """The one value per shot the trend is asked of.

        `at` is the 0-based index into the curve `get_signal` answers;
        `which` is `'mean'`, `'max'`, or `'min'` over that curve. Name one
        or the other, not both: the shot values the caller asked for and
        the shot values the case holds are two different things, and the
        trend must not mix them.
        """
        payload = self.get_signal(uri, path, along=along, indices=indices)
        if not isinstance(payload, dict) or payload.get('kind') != 'curve':
            kind = payload.get('kind') if isinstance(payload, dict) \
                else type(payload).__name__
            raise ValueError(
                'shot %s answers %r for %s: a per-shot value is read off a '
                'curve the case draws along one axis -- name it with `along` '
                'and `indices` -- not a multi-array answer.'
                % (uri, kind, path))
        y = list(payload.get('y') or [])
        if not y:
            raise ValueError(
                'shot %s answers no value for %s: name the axis or element '
                'the case holds the leaf on.' % (uri, path))
        if at is not None:
            if isinstance(at, bool):
                raise ValueError('`at` is a 0-based index into the curve '
                                 'the shot answers, not a true/false flag.')
            if isinstance(at, str) and at.strip().isdigit():
                at = int(at.strip())
            if not isinstance(at, int):
                raise ValueError('`at` is a 0-based index into the curve '
                                 'the shot answers, got %r.' % (at,))
            if not (0 <= at < len(y)):
                raise ValueError(
                    'shot %s holds %d values for %s and at=%d is out of '
                    'range (0 to %d).' % (uri, len(y), path, at, len(y) - 1))
            value = float(y[at])
        else:
            which = (which or 'mean').strip().lower()
            if which not in ('mean', 'max', 'min'):
                raise ValueError('`which` is "mean", "max" or "min", '
                                 'got %r.' % (which,))
            finite = [v for v in y
                      if v is not None and isinstance(v, (int, float))
                      and v == v and abs(v) != float('inf')]
            if not finite:
                raise ValueError(
                    'shot %s answers no finite value for %s: the case does '
                    'not hold the leaf there, so there is no number to '
                    'take the trend on.' % (uri, path))
            if which == 'mean':
                value = sum(finite) / len(finite)
            elif which == 'max':
                value = max(finite)
            else:
                value = min(finite)
        return value

    def campaign(self, cases, path, at=None, which='mean',
                 along=None, indices=None):
        """The trend of a leaf, across a series of shots, in campaign order.

        `cases` is the list of shot URIs, in the order the campaign runs;
        `path` the leaf to read from each shot; `at` the 0-based index into
        the curve the shot answers, or `which` ('mean', 'max', 'min') over
        that curve -- one of the two, not both. The answer carries the
        per-shot values, the least-squares slope over the shot index, first
        to last, min/max and the shots they came from, and a direction.
        `cases` of one, a shot the case does not hold the leaf in, or a
        campaign of all-equal values refuses by name -- each in the words
        that mean it.
        """
        if not isinstance(cases, (list, tuple)):
            raise ValueError('`cases` is the list of shot URIs, in campaign '
                             'order, and %r is not one.' % (cases,))
        if len(cases) < 2:
            raise ValueError('a trend is asked of at least two shots; the '
                             'campaign holds %d.' % len(cases))
        if at is not None and which is not None and \
                which != 'mean':
            raise ValueError('name one of `at` or `which`: the shot-value '
                             'the curve answers and the shot-value the '
                             'caller asked for are two reads, and the trend '
                             'runs on one of them, not a mix of the two.')
        rows = []
        for uri in cases:
            value = self._shotValue(uri, path, at, which, along, indices)
            rows.append({'uri': uri, 'value': value})
        from imasviz.VizAnalysis.trend import trend as ask
        trend = ask([r['value'] for r in rows],
                    labels=[r['uri'] for r in rows])
        self._logFor([r['uri'] for r in rows],
                     'campaign on %s: %d shot(s) -- %s, change %g, '
                     'slope %g per shot, min %g at shot %d, max %g at '
                     'shot %d.'
                     % (path, len(rows), trend['direction'],
                        trend['change'], trend['slope'],
                        trend['min'], trend['argmin'],
                        trend['max'], trend['argmax']))
        return {'path': path, 'rows': rows, 'trend': trend}

    def campaign_report(self, cases, path, at=None, which='mean',
                        along=None, indices=None, name=None):
        """The campaign answer, as a self-contained HTML page: the per-shot
        table, the trend, and the shape it makes across the shots. The file
        lands under `~/.imasviz/reports` like the other reports."""
        answer = self.campaign(cases, path, at=at, which=which,
                               along=along, indices=indices)
        out = self._namedReport(name, len(answer['rows']))
        self._writeCampaignReport(out, leaf=path, rows=answer['rows'],
                                   trend=answer['trend'])
        self._logFor([r['uri'] for r in answer['rows']],
                     'campaign_report wrote %s: %s, %s over %d shot(s).'
                     % (out, path, answer['trend']['direction'],
                        len(answer['rows'])))
        return {'saved_to': out, 'trend': answer['trend']}

    def _writeCampaignReport(self, path, leaf, rows, trend):
        """The campaign page: the per-shot table, the trend numbers, and the
        line the shot values make across the shots. Inline SVG, no fetch, the
        same little style the other reports wear."""
        import html

        def show(value):
            return ('%g' % float(value)) if isinstance(value, float) \
                else str(value)

        # one point per shot, across the width; values mapped to the height
        # on the campaign's own min/max so the line shows the shape, even
        # where the shots cluster
        vmin, vmax = float(trend['min']), float(trend['max'])
        span = (vmax - vmin) or 1.0
        width, height, pad = 340, 120, 16
        n = len(rows)
        step_x = (width - 2 * pad) / max(1, n - 1)
        step_y = (height - 2 * pad) / span
        points = []
        dots = []
        for i, r in enumerate(rows):
            x = pad + i * step_x
            y = pad + (vmax - float(r['value'])) * step_y
            points.append(('%g %g' % (x, y)))
            dots.append('<circle cx="%g" cy="%g" r="2.5"/>' % (x, y))
        parts = [
            '<!doctype html>',
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, '
            'initial-scale=1">',
            '<title>%s</title><style>%s</style></head><body>' % (
                html.escape('campaign of %s' % leaf), _REPORT_CSS),
            '<h1>%s</h1>' % html.escape('campaign of %s' % leaf),
            '<p class="sub">%d shot(s) · %s · change %s · slope %s/shot · '
            'min %s (shot %d) · max %s (shot %d)</p>'
            % (len(rows), trend['direction'], show(trend['change']),
               show(trend['slope']), show(trend['min']), trend['argmin'],
               show(trend['max']), trend['argmax']),
            '<svg width="%d" height="%d" role="img" '
            'aria-label="the trend of %s across the campaign">'
            % (width, height, html.escape(leaf)),
            '<line x1="%g" y1="%g" x2="%g" y2="%g" '
            'stroke="#dde3e7" stroke-width="1"/>'
            % (pad, height - pad, width - pad, height - pad),
            '<polyline fill="none" stroke="#3a707a" stroke-width="1.5" '
            'points="%s"/>' % ' '.join(points),
            ' '.join(dots),
            '</svg>',
            '<table>',
            '<tr><th>shot</th><th>value</th><th>uri</th></tr>',
        ]
        for i, r in enumerate(rows):
            parts.append('<tr><td class="s">%d</td><td class="s">%s</td>'
                         '<td class="q">%s</td></tr>'
                         % (i, show(r['value']), html.escape(r['uri'])))
        parts.append('</table>')
        parts.append('</body></html>')
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(parts))
        except OSError as error:
            raise ValueError('the report could not be written to %s: %s'
                             % (path, error))
