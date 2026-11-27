# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The curve-figure gestures of one IMASViz session: the edits, the stats and the export of the curves a figure holds.

Scaling, shifting, normalising, removing, re-ranging and exporting of the traces a curve figure carries, plus the picture-window and slice-index edits. A refusal is the named `ValueError` the caller gets back.
"""


class CurveOps:
    """The curve figure: its edits, its stats and its export."""

    def scale_curve(self, figure_key, factor, curve=None):
        """Multiply a figure's drawn curve(s) by a constant.

        The factor is kept by the figure beside the values it read for that
        trace (`QVizCurveTransform`), so it is still there when a slider, a
        posed row or a re-read brings other values under the curve: the picture
        then shows the new element at the scale the hand asked for, not the raw
        one. `curve_stats` / `export_curve` read the value back multiplied.
        `curve` is `None` for every curve the figure holds, an index in draw
        order, or a quantity-name substring. `factor` must be a finite number,
        refused by name when it is not. `reset_curve` takes the multiplication
        off (or `plot_one` redraws the unmultiplied curve), because a transform
        is one of the view, not of the quantity in the tree. A window that holds
        no curve to multiply is refused by name, naming what it holds instead.
        """
        import math

        if (isinstance(factor, bool) or not isinstance(factor, (int, float))
                or not math.isfinite(factor)):
            raise ValueError(
                'The factor is %r: a finite number the value may be '
                'multiplied by, not a name, zero, or a boolean.' % (factor,))
        record, curves = self._curveFor(figure_key, curve)
        done = []
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            if x is None or y is None:
                continue
            already = source.transformOf(item)
            source.setTransform(item, already[0] * factor, already[1] * factor)
            done.append(self._curveName(node, rank))
        if not done:
            raise ValueError(
                'The %d curve(s) of "%s" hold no number to multiply, every '
                'one being empty as it stands.' % (len(curves), figure_key))
        self._logFor(record.cases,
                     'scale_curve: %s x %g on %s.'
                     % (', '.join(done), factor, figure_key))
        return {'window': figure_key, 'factor': float(factor),
                'curves': done}

    def shift_curve(self, figure_key, offset, curve=None):
        """Add a constant to a figure's drawn curve(s): a vertical offset.

        The inverse of a subtraction; `reset_curve` takes it off. Everything
        else is the rule of `scale_curve`: the offset is kept by the figure and
        goes back under the values a later read answers, in place, `curve` the
        one or the figure's, and the named refusals the figure's holds earn.
        """
        import math

        if (isinstance(offset, bool) or not isinstance(offset, (int, float))
                or not math.isfinite(offset)):
            raise ValueError(
                'The offset is %r: a finite number the value may be shifted '
                'by, not a name or a boolean.' % (offset,))
        record, curves = self._curveFor(figure_key, curve)
        done = []
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            if x is None or y is None:
                continue
            already = source.transformOf(item)
            source.setTransform(item, already[0], already[1] + offset)
            done.append(self._curveName(node, rank))
        if not done:
            raise ValueError(
                'The %d curve(s) of "%s" hold no number to shift, every one '
                'being empty as it stands.' % (len(curves), figure_key))
        self._logFor(record.cases,
                     'shift_curve: %s + %g on %s.'
                     % (', '.join(done), offset, figure_key))
        return {'window': figure_key, 'offset': float(offset),
                'curves': done}

    def normalize_curve(self, figure_key, mode='max', curve=None):
        """Divide a figure's drawn curve(s) by a reference of their own.

        `mode` is `max` (divide by the largest sample -- the peak goes to 1),
        `first` (divide by the first sample, the one at index 0 -- that
        sample goes to 1), or `mean` (divide by the mean -- the mean goes to
        1); `curve` selects the curve or the figure's as elsewhere. The
        reference is read off the curve as it stands, so a shift already on
        of it is what the reference is taken from. It is the divisor from
        then on: a curve the figure re-reads under a slider comes back
        divided by that same reference, not by the peak of the element it is
        now -- two curves of one figure stay comparable, which is the whole
        reason for dividing them. A reference that is zero or not a number is
        refused by name -- the division is then `inf` or
        `nan`, and the reader would read a picture full of them for a
        quantity nobody divided by anything. `reset_curve` restores the
        unnormalized values.
        """
        if mode not in ('max', 'first', 'mean'):
            raise ValueError(
                'The mode is %r: max, first, or mean -- the one the value '
                'is divided by.' % (mode,))
        import numpy as np

        record, curves = self._curveFor(figure_key, curve)
        done = []
        reference = None
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            if x is None or y is None:
                continue
            values = np.asarray(y, dtype=float)
            if mode == 'max':
                reference = float(np.nanmax(values))
            elif mode == 'first':
                reference = float(values[0])
            else:
                reference = float(np.nanmean(values))
            if not (np.isfinite(reference) and reference != 0.0):
                raise ValueError(
                    'The reference of %s in the %s mode is %r: zero or '
                    'not a number, so the division is undefined (it would '
                    'be the inf or nan of a picture full of no signal). '
                    'Name a curve that holds a non-zero value to %s from.'
                    % (self._curveName(node, rank), mode, reference, mode))
            already = source.transformOf(item)
            source.setTransform(item, already[0] / reference,
                                already[1] / reference)
            done.append(self._curveName(node, rank))
        if not done:
            raise ValueError(
                'The %d curve(s) of "%s" hold no number to normalize, every '
                'the value it holds being empty.'
                % (len(curves), figure_key))
        self._logFor(record.cases,
                     'normalize_curve: %s / %s (=%g) on %s.'
                     % (', '.join(done), mode, reference, figure_key))
        return {'window': figure_key, 'mode': mode,
                'reference': float(reference), 'curves': done}

    def reset_curve(self, figure_key, curve=None):
        """Take the transforms off: put the curve(s) back to the data the figure
        holds for them.

        The figure keeps, per trace, the values its last read answered and the
        (factor, offset) a hand laid on them; this takes the affine off and
        leaves those values where the read left them. Which is the element the
        row of a band is posed at when a slider moved it -- not the element the
        hand started on, which is what a stashed copy of the first capture would
        have brought back under a curve the figure had already moved. A curve
        nobody transformed keeps the data it was drawn with and is not in the
        answer's list: nothing to reset is refused by name, saying what is
        held as drawn already and what a re-plot would give back, so the
        caller does not mistake a clean window for an empty one.
        """
        record, curves = self._curveFor(figure_key, curve)
        restored = []
        held = 0
        for node, rank, item, source in curves:
            held += 1
            if not source.clearTransform(item):
                continue
            restored.append(self._curveName(node, rank))
        if not restored:
            raise ValueError(
                'No transform to take off on "%s": the %d curve(s) it '
                'holds stand as drawn (a reset asks for a curve that was '
                'scaled, shifted, or normalized, or a re-plot with '
                'plot(mode="single")).' % (figure_key, held))
        self._logFor(record.cases,
                     'reset_curve: %s back to the data as drawn, on %s.'
                     % (', '.join(restored), figure_key))
        return {'window': figure_key, 'restored': restored}

    def remove_curve(self, figure_key, curve=None):
        """Take a curve off a figure, or every one when `curve` is left out.

        The curve leaves the plot and the figure forgets it: its legend entry
        goes with it, and the figure's `curveCount` answers the rest. The
        figure is the one the curve was drawn in (a curve figure: a table and
        a stacked window each draw a panel and are not a single figure to
        remove a curve from). A name or an index no curve answers is refused
        by name, the curve(s) it does hold being said alongside, and a
        window that holds no curve is refused the same way.
        """
        record, frame = self._windowForKey(figure_key)
        if not hasattr(frame, 'removeCurve'):
            raise ValueError(
                'The window "%s" (%s) is not a single figure a curve can '
                'be removed from: it holds %s, and the figure a single '
                'curve was drawn in is what remove_curve takes.'
                % (figure_key, record.kindLabel, record.kindLabel))
        # `_curveFor` resolves what to drop; this maps it to the indices
        # of the figure's own draw order, so the curves the answer named
        # and the ones the figure forgets are the same, and a name that
        # matched several of them is one removal per match, not one that
        # names all.
        record, curves = self._curveFor(figure_key, curve)
        if curve is None:
            count = frame.removeCurve()
        else:
            indexes = []
            for node, rank, item, source in curves:
                for i, trace in enumerate(frame._curves):
                    if trace.curve is item:
                        indexes.append(i)
                        break
            if not indexes:
                raise ValueError(
                    'The named curve is not on "%s" in a place remove_curve '
                    'can take it from.' % figure_key)
            for i in sorted(indexes, reverse=True):
                frame.removeCurve(i)
            count = frame.curveCount()
        self._logFor(record.cases,
                     'remove_curve: %s left on %s.' % (count, figure_key))
        return {'window': figure_key, 'curves_left': int(count)}

    def set_axis_range(self, figure_key, xmin=None, xmax=None, ymin=None,
                       ymax=None, auto=False):
        """The window (the range) of a figure's axes, set by name and number.

        Pin the abscissa's window with `xmin` and `xmax` together, the
        ordinate's with `ymin` and `ymax` together, both at once, or
        `auto=True` to clear the pins and let the view re-fit to the curves.
        Partial (one bound of a pair) is refused because a range is two
        bounds; so is a bound that is not a finite number or in the wrong
        order (`xmin` must be less than `xmax`, `ymin` less than `ymax`)
        -- an inversion is one the reader misreads. The window is what
        pyqtgraph holds on screen after the call, returned so the caller
        reads the same numbers the figure shows.

        A curve figure takes one axis set. A picture window takes the same
        span on the axis set of **each** of its pictures -- the window is
        one scale and one span, so a time zoom of a strip whose abscissa is
        its time is the `x` range, in the seconds its time axis holds, and
        the answer reports that one span. A table and a stacked view keep
        one axis set per panel and are refused by name.
        """
        import math

        record, frame = self._windowForKey(figure_key)
        boxes = self._viewBoxesOf(frame, figure_key)

        def finite(bound, value):
            if value is None:
                return
            if (isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)):
                raise ValueError(
                    '%s is %r: a finite number the bound must be, not a '
                    'name or a boolean.' % (bound, value))

        def pair(boundA, a, boundB, b):
            if (a is not None) != (b is not None):
                raise ValueError(
                    'The axis is a pair: name %s and %s together, or leave '
                    'both out.' % (boundA, boundB))

        pair('xmin', xmin, 'xmax', xmax)
        pair('ymin', ymin, 'ymax', ymax)
        finite('xmin', xmin); finite('xmax', xmax)
        finite('ymin', ymin); finite('ymax', ymax)
        if auto and (xmin is not None or xmax is not None
                     or ymin is not None or ymax is not None):
            raise ValueError(
                '`auto` clears the manual pins and is not a bound: pick '
                'the auto ask or the manual one, not both.')

        if auto:
            for box in boxes:
                box.enableAutoRange()
            xR, yR = boxes[0].state['viewRange']
            self._logFor(record.cases,
                         'set_axis_range: %s re-fits (the auto range is '
                         'back on).' % figure_key)
            return {'window': figure_key, 'auto': True,
                    'xRange': [float(xR[0]), float(xR[1])],
                    'yRange': [float(yR[0]), float(yR[1])]}

        if xmin is None and ymin is None:
            raise ValueError(
                'A range needs at least one axis to pin: x (`xmin`, '
                '`xmax`), y (`ymin`, `ymax`), or `auto=True` to clear '
                'the pins.')
        if xmin is not None and xmin >= xmax:
            raise ValueError(
                'The x range is inverted (%g >= %g): `xmin` must be less '
                'than `xmax`.' % (xmin, xmax))
        if ymin is not None and ymin >= ymax:
            raise ValueError(
                'The y range is inverted (%g >= %g): `ymin` must be less '
                'than `ymax`.' % (ymin, ymax))
        for box in boxes:
            box.disableAutoRange()
        for box in boxes:
            if xmin is not None:
                box.setXRange(xmin, xmax)
            if ymin is not None:
                box.setYRange(ymin, ymax)
        xR, yR = boxes[0].state['viewRange']
        self._logFor(record.cases,
                     'set_axis_range: %s pinned, x=%s, y=%s.'
                     % (figure_key,
                        '[%g..%g]' % (xmin, xmax) if xmin is not None
                        else 'left to re-fit',
                        '[%g..%g]' % (ymin, ymax) if ymin is not None
                        else 'left to re-fit'))
        return {'window': figure_key, 'pinned': True,
                'xRange': [float(xR[0]), float(xR[1])],
                'yRange': [float(yR[0]), float(yR[1])]}

    def set_log_scale(self, figure_key, x=None, y=None):
        """A log axis, by name: `x=True/False` and `y=True/False` for the
        abscissa/ordinate, going to log or linear. Leave the one you are
        not touching out, and name at least one of the two.

        The axis is the one of a curve figure -- a single figure the curves
        were drawn in, the one the range and the inset tools address. Refused
        by name: no axis named, a `True/False` the bound is not, and a log
        axis turned on where the drawn values cross zero or below (log is
        undefined there, and pyqtgraph would hide those points so the figure
        read as "no data" where it holds a half-empty axis). A shift of the
        values (a `shift_curve` to clear negative values) is the honest
        answer for a flux loop that runs through zero.

        Going log resamples the traces along log10 and makes the axis tick
        logarithmically. A span pinned with `configure_axes(operation="range")`
        is carried through the change on the axis it belongs to -- the same
        window on the logarithms going in, on the powers of ten coming back --
        so the scale move never throws the reading away. A pinned span that
        reaches zero or below has no logarithm to be carried to: the view
        re-fits on that axis and the answer says which one in `refitted`.
        """
        import numpy as np

        if x is None and y is None:
            raise ValueError(
                'An axis is named: `x`, `y`, or both -- `True` for log, '
                '`False` for linear.')
        for name, value in (('x', x), ('y', y)):
            if value is None:
                continue
            if not isinstance(value, bool):
                raise ValueError(
                    '%s is %r: `True` to go log, `False` to go back to '
                    'linear.' % (name, value))
        record, frame = self._windowForKey(figure_key)
        plot = self._plotItemOf(frame, figure_key)
        for axis, on in (('x', x), ('y', y)):
            if on is not True:
                continue
            values = []
            for node, rank, item, source in self._curveFor(figure_key)[1]:
                xvals, yvals = self._curveData(item)
                values.append(xvals if axis == 'x' else yvals)
            values = [np.asarray(v, dtype=float).reshape(-1)
                      for v in values if v is not None and len(v)]
            if not values:
                continue
            joined = np.concatenate(values)
            finite = joined[np.isfinite(joined)]
            if finite.size == 0:
                continue
            n_bad = int(np.sum(finite <= 0))
            if n_bad:
                raise ValueError(
                    'A log %s axis is undefined where a value is zero or '
                    'negative: %d of the %d sampled point%s read so. The '
                    'picture would hide them and read as empty where it '
                    'holds a half-empty axis, so the log ask on it is '
                    'refused, and `transform_curve(operation="shift")` '
                    '(up to the zero or above) '
                    'is the answer to give it back.'
                    % (axis, n_bad, int(finite.size),
                       '' if finite.size == 1 else 's'))
        # The ask goes to the plot item, not to the view box, and that is the
        # whole of the difference. In pyqtgraph 0.13.7 a log axis is applied
        # in two places: each `PlotDataItem` resamples itself along log10 and
        # the `AxisItem` draws log ticks, the axis then informing the view
        # box. `ViewBox.setLogMode` -- which the library's own right-click
        # menu never calls on its own -- only records a flag, read back by
        # `_effectiveLimits` to clamp pan and zoom. Measured offscreen: it
        # leaves the drawn values at [10, 100, 1000, 10000] while its state
        # reads [False, True], so a gesture that asked only the view box
        # answered "done" over an untouched picture.
        box = plot.getViewBox()
        # Installing the scale runs `updateLogMode`, which re-enables the auto
        # range on both axes: a span a hand pinned is dropped by the change
        # unless it is carried over -- across the mapping on the axis asked,
        # unchanged on the one it was not asked to touch. A span whose two ends
        # are not both above zero has no logarithm to be carried to, and the
        # view re-fits there: said in the answer and in the log, not left for
        # the reader to notice by a window that moved on its own.
        spans = []
        for name, index, side, on in (('x', 0, 'bottom', x),
                                      ('y', 1, 'left', y)):
            if box.state['autoRange'][index]:
                continue
            was = [float(v) for v in box.state['viewRange'][index]]
            if on is None or bool(plot.getAxis(side).logMode) == on:
                span = was
            elif on:
                span = ([float(np.log10(v)) for v in was]
                        if min(was) > 0.0 else None)
            else:
                span = [float(10.0 ** v) for v in was]
            spans.append((name, span))
        plot.setLogMode(x=None if x is None else bool(x),
                        y=None if y is None else bool(y))
        for name, span in spans:
            if span is not None:
                box.setRange(**{'%sRange' % name: span}, padding=0.)
        # The two axes the figure draws are what the picture wears; the view
        # box flag is derived from them, through the axis-view link.
        logMode = [bool(plot.getAxis('bottom').logMode),
                   bool(plot.getAxis('left').logMode)]
        refitted = [name for name, span in spans if span is None]
        self._logFor(record.cases,
                     'set_log_scale: %s, x=%s, y=%s (now %s).%s'
                     % (figure_key, x, y, str(logMode),
                        '' if not refitted else
                        ' The pinned %s span has no logarithm to be carried '
                        'to: the view re-fits there.' % ', '.join(refitted)))
        answer = {'window': figure_key, 'x': logMode[0],
                  'y': logMode[1], 'logMode': logMode,
                  'xRange': [float(v) for v in box.state['viewRange'][0]],
                  'yRange': [float(v) for v in box.state['viewRange'][1]]}
        if refitted:
            answer['refitted'] = refitted
        return answer

    def invert_axis(self, figure_key, x=None, y=None):
        """Invert (flip) an axis: the negative side goes the other way, and
        the reader's reading of the picture follows it.

        `x=True/False` inverts/puts back the abscissa, `y=True/False` the
        ordinate, leaving the one you do not touch out and naming at least
        one of the two. The axis is the one of a figure a single curve was
        drawn in; naming a window that is not one of those is refused by
        name. Inversion and range are independent: a range you have pinned
        keeps it where the values sit, and the picture reads reversed.
        """
        if x is None and y is None:
            raise ValueError(
                'An axis is named: `x`, `y`, or both -- `True` to invert '
                'the picture, `False` to put it back.')
        for name, value in (('x', x), ('y', y)):
            if value is None:
                continue
            if not isinstance(value, bool):
                raise ValueError(
                    '%s is %r: `True` to invert, `False` to put back.'
                    % (name, value))
        record, frame = self._windowForKey(figure_key)
        box = self._plotItemOf(frame, figure_key).getViewBox()
        if x is not None:
            state = box.state
            state['xInverted'] = bool(x)
            box.setState(state)
        if y is not None:
            state = box.state
            state['yInverted'] = bool(y)
            box.setState(state)
        state = box.state
        self._logFor(record.cases,
                     'invert_axis: %s, x=%s, y=%s.'
                     % (figure_key, x, y))
        return {'window': figure_key,
                'xInverted': bool(state.get('xInverted', False)),
                'yInverted': bool(state.get('yInverted', False))}

    def set_image_window(self, figure_key, start=None, count=None):
        """The window a figure's pictures sit on: moved, or resized, by name.

        `start` is where the window sits on the axis it reads across -- the
        pictures are re-read in place, one of them per element, and the scale
        and the controls stay put while the window moves; `count` is how
        many pictures the window holds and the resize rebuilds them on the
        same start, the same pinned axes, and the scale a hand settled.
        The ask names neither bound and is refused: a window someone moved
        is named by where it sits and how wide it is, and an ask that says
        nothing is not a move the window can answer.

        The answer is the state the window holds after the call -- the axis
        it reads across, its start and its count, the extent the axis holds,
        and the label of each picture the window shows, the element it is
        and, when the axis carries a value at that element (a time axis does),
        the value it carries, so a window of three pictures answers the three
        elements it holds and the answer is the same numbers the titles of
        the pictures spell.

        Refused by name, and each refusal says the shape of the window that
        was tried and the gesture that answers the question instead of
        repeating the one that failed: a window that is not an image window
        has no pictures and no axis read across them; an image window that
        holds a single picture has no window to move or resize, and the span
        of that one picture is the axis range -- `set_axis_range` -- of the
        axis it drew; a `start` or `count` past the extent the axis holds is
        the extent itself, named, not a slip past it.
        """
        record, frame = self._windowForKey(figure_key)
        pictures = getattr(frame, 'plotItems', None)
        if not callable(pictures):
            # Naming the shape the window holds is what tells the caller
            # which gesture it asked -- the curves one, or the panels' own.
            pgPlot = getattr(frame, 'pgPlotWidget', None)
            if pgPlot is not None and hasattr(pgPlot, 'getViewBox'):
                raise ValueError(
                    'The window "%s" is a figure of curves: it holds traces, '
                    'not a window of pictures, so there is no window to move '
                    'or resize on it, and the span of its axes is the one '
                    'configure_axes(operation="range") pins. Name the '
                    'figure the pictures were drawn in.' % figure_key)
            raise ValueError(
                'The window "%s" is not an image window: it is not a figure '
                'of pictures, so there is no window of them to move or '
                'resize, and the panels it holds each keep their own '
                'answers. Name the figure the pictures were drawn in.'
                % figure_key)
        sl = getattr(frame, 'frameAxis', None)
        sl = sl() if callable(sl) else None
        if sl is None:
            raise ValueError(
                'The window "%s" holds one picture, not a window of them: '
                'it was not read across an axis, so there is no window to '
                'move or resize, and the span of the one it holds is what '
                'configure_axes(operation="range") pins on the axis it '
                'drew.' % figure_key)
        controls = getattr(frame, 'framesControls', None)
        if controls is None:
            raise ValueError(
                'The window "%s" is an image window but holds no control on '
                'the axis it reads across, so the window there is not one '
                'that can be moved or resized.' % figure_key)
        if start is None and count is None:
            raise ValueError(
                'A window moved, or resized: `start` is where it sits on '
                'the axis it reads across, `count` how many pictures it '
                'holds -- and naming neither says nothing the window can '
                'answer.')
        if start is not None:
            try:
                start = int(start)
            except (TypeError, ValueError):
                raise ValueError(
                    'The window sits on the axis its pictures are '
                    'elements of, at a whole element: %r is not one.'
                    % (start,))
            if start < 0:
                raise ValueError(
                    'The window sits from element 0 of the axis its '
                    'pictures are elements of, and %d is before it.'
                    % start)
            if length_known := (getattr(sl, 'length', None) is not None):
                extent = int(sl.length)
                if start >= extent:
                    raise ValueError(
                        'The axis this window reads across holds %d '
                        'elements (0 to %d), and %d is past the last one: '
                        'a window with no picture to draw would be blank '
                        'to the eye and blank to the answer.'
                        % (extent, extent - 1, start))

        if count is not None:
            # The resize is the window's own: it derives the slider's reach
            # from the new count and rebuilds the pictures on the start the
            # window holds, refusing by name a count the axis cannot hold.
            frame.frameCount(count)
        if start is not None:
            frames = controls.setStart(start)
            if frames is False:
                raise ValueError(
                    'The window "%s" has no control on the axis its '
                    'pictures are elements of, so a position to sit it at '
                    'is not one it holds.' % figure_key)

        count_actual = int(controls.count())
        start_actual = int(controls.start())
        length = None if getattr(sl, 'length', None) is None \
            else int(sl.length)
        # The label of each picture the window shows -- the element it is,
        # and the value the axis carries at that element when it carries
        # one. A time axis does, and a window of three slices is the only
        # way to compare them, so the answer says the three times, not
        # three element ranks. The value is read once, and the label is
        # posed on it per element, in the same shape the titles of the
        # pictures spell.
        axis = getattr(sl, 'axis', None)
        values = None
        if axis is not None and getattr(axis, 'is_time', False):
            try:
                from imasviz.VizDataAccess.QVizTensorDataAccess \
                    import QVizTensorExtractor
                node = frame.treeNode()
                axesSpec = frame.accessFor(node).plan(
                    node, frame, as_function_of_time=False)[0]
                values = QVizTensorExtractor(node.getIDSRef()).timeBase(axesSpec)
            except Exception:
                values = None
        images = []
        for index in range(start_actual, start_actual + count_actual):
            if values is not None:
                from imasviz.VizDataAccess.QVizSlices import frameLabel
                images.append(frameLabel(axis, index, values))
            else:
                images.append(index)
        self._logFor(record.cases,
                     'set_image_window: %s moved to start=%d, %d picture(s) '
                     'of the %s it reads across.'
                     % (figure_key, start_actual, count_actual,
                        getattr(sl, 'label', 'axis')))
        return {'window': figure_key,
                'axis': getattr(sl, 'label', None),
                'start': start_actual,
                'count': count_actual,
                'length': length,
                'pictures': images}

    def set_slice_index(self, figure_key, axis=None, index=None):
        """The slider of a band, posed at a named index, on the window
        that holds the band.

        `axis` is the row of the band the gesture names -- `time_slice`,
        `psi`, `profiles_2d` -- in the words the band spells the axis in,
        and `index` is the element the row is posed at, the bound the row
        holds being the one a refusal names when the index passes it. The
        row moves the band the way the user moves it: the slider of the
        row, and the window re-reads the one the row is posed at, without
        the other rows moving under them.

        The answer is the state the band holds after the call: the rows
        it is, the one that moved, the index it is posed at, and its
        length -- so the caller reads back the state the window holds,
        and a row the band holds that the gesture did not move says so
        in the answer, not in a guess.

        Refused by name, each refusal saying the shape of the window
        that was tried and the gesture that answers the question instead
        of repeating the one that failed: a window not one the band of
        the gesture sits on (a table keeps one answer per panel, and a
        stacked window one per panel of the two); a window that is a
        picture window but holds no band for it (a strip whose axis the
        pictures were laid on is on screen, side by side, and is what
        the `set_image_window` gesture moves and resizes -- there is no
        row for an axis the window already shows); a window that holds
        the band but not the axis it was asked to move (the rows it does
        hold are the ones the refusal names, and the span of the axis it
        drew is `set_axis_range`); an index outside the extent the row
        holds (the bound it holds, named, not a slip past it).
        """
        record, frame = self._windowForKey(figure_key)

        def _framesPointer():
            # The axis the pictures are laid across: it is already on
            # screen, one picture per element, so a row of a band would
            # ask for what the window shows -- the window it sits on is
            # what `set_image_window` moves and resizes. The frame axis
            # is a QVizSlice; its `label` is the `sliceLabel` of the
            # axis underneath it, already spelled the way the band
            # spells the axes it holds.
            sl_axis = getattr(frame, 'frameAxis', None)
            sl_axis = sl_axis() if callable(sl_axis) else None
            word = (str(sl_axis.label)
                    if sl_axis is not None else 'the strip')
            return ValueError(
                'The window "%s" holds no row for that axis: its '
                'pictures are the axis it reads across (here %s), one '
                'picture per element, side by side, and the window '
                'they sit on is what configure_axes'
                '(operation="image_window") moves (start) '
                'and resizes (count) -- a row of a band is not one '
                'for an axis the window already shows.'
                % (figure_key, word))

        def _frameAxisWord():
            sl_axis = getattr(frame, 'frameAxis', None)
            sl_axis = sl_axis() if callable(sl_axis) else None
            return str(getattr(sl_axis, 'label', '')
                       or '') if sl_axis is not None else ''

        frames_key = getattr(frame, 'framesKey', None)
        frames_key = frames_key() if callable(frames_key) else None
        sliceControls = getattr(frame, 'sliceControls', None)
        if sliceControls is None:
            raise ValueError(
                'The window "%s" is not one the band of sliders of the '
                'gesture sits on: a curve figure of one axis is (the rows '
                'of the band the gesture addresses), an image window is '
                '(one row per axis it pins), and this one is not, holding '
                'no band and no row to move. Name the curve figure, or '
                'the image window, that holds the axis.' % figure_key)
        rows = list(sliceControls.rows())
        word = str(axis if axis is not None else '').strip().lower()
        if not rows:
            fa_word = _frameAxisWord()
            if frames_key is not None:
                if not word or word == fa_word:
                    # The axis the gesture named is the one the window
                    # is read across, or it is not one at all: the
                    # refusal is the one that moves the window, and it
                    # names the axis the window moves on.
                    raise _framesPointer()
                # The axis is drawn inside the pictures, where a slider
                # would sit under it: it is on screen, not a control,
                # and its span is the range set_axis_range pins on each
                # of the pictures.
                raise ValueError(
                    'The window "%s" holds no row for that axis: it is '
                    'drawn inside the pictures, and a slider under an '
                    'axis that is on screen would move a window the '
                    'picture already shows. Its pictures are the axis the '
                    'window is read across (here %s), which is what '
                    'configure_axes(operation="image_window") moves '
                    '(start) and resizes (count); '
                    'the span of the axis it drew is what '
                    'configure_axes(operation="range") '
                    'pins, on each of its pictures.'
                    % (figure_key, fa_word or 'the strip'))
            raise ValueError(
                'The window "%s" holds no band of sliders: the axes it '
                'pins are none, so the axis the gesture names is not a '
                'row of it, and the one it drew is on screen rather than '
                'a control to move -- the span of the axes it drew is '
                'what configure_axes(operation="range") pins.'
                % figure_key)
        if not word:
            raise ValueError(
                'The axis of the row to move is named in the words the '
                'band spells the axes it holds, not the empty string: %s.'
                % ', '.join(sorted(row.label for row in rows)))
        if frames_key is not None and word == _frameAxisWord():
            # The axis the pictures are laid across is already on
            # screen: a row for it would ask for what they show.
            raise _framesPointer()
        exact = [row for row in rows
                 if str(row.label).strip().lower() == word
                 or str(row.key).strip().lower() == word]
        if exact:
            row = exact[0]
        else:
            partial = [row for row in rows
                       if word in str(row.label).strip().lower()
                       or word in str(row.key).strip().lower()]
            if not partial:
                raise ValueError(
                    'The band of the window "%s" holds: %s -- "%s" names '
                    'no row this band holds. Name one of the rows of the '
                    'band this figure holds, in the words the band spells '
                    'the axis it pins.'
                    % (figure_key,
                       ', '.join(sorted(row.label for row in rows)),
                       axis))
            if len(partial) > 1:
                raise ValueError(
                    '"%s" names several rows of the band of the window '
                    '"%s": %s -- name the one, in full, that the gesture '
                    'is moving.'
                    % (axis, figure_key,
                       ', '.join(sorted(row.label for row in partial))))
            row = partial[0]
        try:
            index = int(index)
        except (TypeError, ValueError):
            raise ValueError(
                'The index of the row "%s" is a whole number, not %r: the '
                'row holds a range from 0 to its extent, and a value in '
                'that range is what the row is posed at.'
                % (row.label, index))
        if row.length is not None:
            bound = max(int(row.length), 1)
            if index < 0 or index >= bound:
                raise ValueError(
                    'The row "%s" of the window "%s" holds an element '
                    'from 0 to %d, and %d is outside it: the bound the '
                    'row holds is the one the row holds, not a guess '
                    'past the extent the tree names.'
                    % (row.label, figure_key, bound - 1, index))
        # The row moves and the window re-reads the one the row is posed
        # at, in the place the row is posed to move it: the other rows of
        # the band stay where they are, because the gesture is one row,
        # one index, and the window is the one the slider of the row is
        # the control of.
        row.setIndex(index)
        self._logFor(record.cases,
                     'set_slice_index: %s posed the row "%s" at index %d '
                     '(%s held, %d to %d).'
                     % (figure_key, row.label, index,
                        'the bound' if row.length is None
                        else 'held', 0, max(int(row.length or 1), 1) - 1))
        return {'window': figure_key,
                'axis': row.label,
                'index': int(row.index()),
                'length': (None if row.length is None else int(row.length)),
                'rows': {row2.label: int(row2.index()) for row2 in rows}}

    def curve_stats(self, figure_key, curve=None):
        """The numbers of a figure's drawn curves, one per curve.

        `n` the sample count, `min`/`max`/`mean`/`std` the finite minimum,
        maximum, mean and standard deviation of the values, `nan`/`inf` the
        count of the non-number entries, and -- where both x and y are
        present and the same length -- `peak_value` the largest magnitude
        the values take and `peak_at` the abscissa it sits at. The read is
        the one `get_signal` uses on the same leaf, so a figure it holds
        and its answer agree: the values of a figure of one quantity and the
        values of a tree read of the same quantity differ only by the
        transform this family of gestures has applied to the figure, not
        by a different quantity.

        `curve` targets one (an index in draw order or a name substring) or
        every curve the figure holds; the window is the one a single curve
        was drawn in, the refusal naming the window that draws a picture
        this does not stat.
        """
        import numpy as np

        record, curves = self._curveFor(figure_key, curve)
        out = []
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            entry = dict(self.curveStats((x, y)))
            label = self._curveName(node, rank)
            if x is not None and y is not None and len(y):
                xs = np.asarray(x, dtype=float).reshape(-1)
                ys = np.asarray(y, dtype=float).reshape(-1)
                if xs.size and ys.size and xs.size == ys.size:
                    mask = np.isfinite(ys)
                    if mask.any():
                        which = int(np.where(mask, np.abs(ys),
                                             0.0).argmax())
                        entry['peak_value'] = float(ys[which])
                        entry['peak_at'] = float(xs[which])
            entry['name'] = label
            entry['rank'] = int(rank)
            out.append(entry)
        if not out:
            raise ValueError(
                'The window "%s" held no curve to stat.' % figure_key)
        self._logFor(record.cases,
                     'curve_stats: %d curve(s) of %s.'
                     % (len(out), figure_key))
        return {'window': figure_key, 'count': len(out), 'curves': out}

    def export_curve(self, figure_key, curve=None, format='csv', name=None):
        """The x/y of a figure's drawn curves, as a file.

        The values as they stand -- any transform this family has put on
        them (a scale, a shift, a normalize) is in the file, so what a
        reader opens is the same as the figure the analyst sees. `curve`
        targets one or the figure's as elsewhere. `format` is `csv`
        (default: one line per sample, two when it is one curve, a header
        per curve in the label order when it is more) or `json` (one object
        per curve, the x and y arrays and the name).

        The file lands in `~/.imasviz/exports` under the guard of the
        configurations, and `name` -- when it is one -- is a name inside
        that folder, not a place (`/` in it is refused by name). A window
        that holds no curve with a value to write is refused the same way,
        saying how many it tried and how many were empty.
        """
        record, curves = self._curveFor(figure_key, curve)
        if format not in ('csv', 'json'):
            raise ValueError(
                '`format` is %r: `csv` or `json`, the shape the file '
                'comes in.' % (format,))
        rows = []
        empty = 0
        for node, rank, item, source in curves:
            x, y = self._curveData(item)
            if x is None or y is None or len(y) == 0:
                empty += 1
                continue
            rows.append((self._curveName(node, rank), x, y))
        if not rows:
            raise ValueError(
                'None of the %d curve(s) of "%s" holds a value to write '
                '(the %d it tried all stand empty as they are).'
                % (len(curves), figure_key, empty))
        path = self._namedExport(name, format, len(rows))
        if format == 'csv':
            with open(path, 'w', newline='') as file:
                for label, x, y in rows:
                    file.write('# %s\n' % label)
                    for i in range(len(y)):
                        file.write('%r,%r\n' % (x[i], y[i]))
        else:
            import json

            with open(path, 'w') as file:
                json.dump(
                    {'window': figure_key,
                     'curves': [{
                         'name': label,
                         'x': [float(value) for value in x],
                         'y': [float(value) for value in y]}
                        for label, x, y in rows]},
                    file, indent=2)
        self._logFor(record.cases,
                     'export_curve wrote %s: %d curve(s) of %s.'
                     % (path, len(rows), figure_key))
        return {'saved_to': path, 'curves': len(rows),
                'empty': int(empty)}

    def _viewBoxesOf(self, frame, figure_key=None):
        """One axis set per drawn picture: the one of a curve figure, or the
        one of each picture of a picture window, in screen order.

        A picture window answers the span with **one** number pair and wears
        it on all of its pictures: the window is one scale and one span, so
        a time zoom of a strip whose abscissa is its time is the `x` range
        in the seconds the time axis holds. A curve figure answers with its
        single `pgPlotWidget.getViewBox()`. A table and a stacked view keep
        one axis set per panel, and a picture window that has drawn nothing
        has no axis set at all -- each refusal names the window and the
        shape it holds, and the caller learns what to ask next.
        """
        pictures = getattr(frame, 'plotItems', None)
        if callable(pictures):
            items = list(pictures())
            if items:
                boxes = []
                for item in items:
                    view = getattr(item, 'getViewBox', None)
                    if view is None:
                        raise ValueError(
                            'The window "%s" holds pictures with no axis set '
                            'a span can be set on, so a range cannot be '
                            'pinned on them.' % (figure_key or 'this window'))
                    boxes.append(view())
                if boxes:
                    return boxes
            raise ValueError(
                'The window "%s" is a picture window that drew no picture, '
                'and a range needs the drawn picture to sit on: draw the '
                'quantity first, and the span is the one '
                'configure_axes(operation="range") '
                'pins.' % (figure_key or 'this window'))
        pgPlot = getattr(frame, 'pgPlotWidget', None)
        if pgPlot is None or not hasattr(pgPlot, 'getViewBox'):
            raise ValueError(
                'The window "%s" is not a single figure whose span this '
                'gesture pins: a figure of curves holds one axis set, and '
                'a picture window takes the span of its pictures -- this '
                'one is neither, its panels each keeping their own answer '
                'on their own. Name the figure a curve was drawn in, or '
                'the one the pictures of one quantity are drawn in.'
                % (figure_key or 'this window'))
        return [pgPlot.getViewBox()]

    def _plotItemOf(self, frame, figure_key=None):
        """The single figure a curve figure draws into: `pgPlotWidget`'s PlotItem.

        The two axis gestures address it, each on its own half: the log mapping
        is applied by the figure over its traces and its axes and the view box
        is only told afterwards, while an inversion is a property of the axis
        mapping the view box holds. A table and a stacked window have one panel
        per picture and keep their own, the flux-surface figure draws inside a
        graphics layout, and a picture window is the span of its own pictures --
        the one `set_axis_range` answers. Each refusal names the window the
        caller tried, and the gesture that answers it, so the refusal the caller
        reads says what to do next instead of repeating the call.
        """
        if callable(getattr(frame, 'plotItems', None)):
            raise ValueError(
                'The window "%s" is a picture window: the log and inversion '
                'gestures address the figure a single curve was drawn in, '
                'and this one holds pictures, whose span is the one '
                'configure_axes(operation="range") pins. Name the figure '
                'the curve was drawn '
                'in.' % (figure_key or 'this window'))
        pgPlot = getattr(frame, 'pgPlotWidget', None)
        if pgPlot is None or not hasattr(pgPlot, 'getPlotItem'):
            raise ValueError(
                'The window "%s" draws no single figure whose axes a log '
                'scale or an inversion can be set on: a curve figure '
                'does, and the table panels and the flux-surface figure do '
                'not. Name the figure the single curve was drawn in.'
                % (figure_key or 'this window'))
        return pgPlot.getPlotItem()

    def _curveName(self, node, rank):
        """The name a manipulated curve carries in an answer.

        The label of the quantity it came from, and its rank among the
        traces that quantity drew when more than one -- the one the legend
        shows and the session files it by.
        """
        label = self._nodeLabel(node)
        return label if rank == 0 else '%s (trace %d)' % (label, rank)

    def _namedExport(self, name, ext, count):
        """The file an export writes: under `~/.imasviz/exports`, the guard
        of the configurations, and the name the caller said -- or the one
        the export is, when it said none. `ext` is the extension it writes
        with (`csv` or `json`), and the name that ends in it is stripped
        so the file is `name.csv` under `~/.imasviz/exports` either way."""
        import os
        import time

        home = os.environ.get('HOME')
        if not home:
            raise ValueError(
                'No HOME in the environment: the exports folder under it '
                'cannot be named.')
        folder = os.path.join(home, '.imasviz', 'exports')
        if not os.path.isdir(folder):
            os.makedirs(folder)
        typed = (name or '').strip()
        if typed.endswith('.' + ext):
            typed = typed[:-(len(ext) + 1)]
        if not typed:
            typed = 'export-' + time.strftime('%Y%m%d-%H%M%S') + '-%d' % count
        if os.path.sep in typed or (os.path.altsep and os.path.altsep
                                    in typed) or typed in ('.', '..'):
            raise ValueError(
                '"%s" is not a file name: it names a place, not an export. '
                'Name one inside %s.' % (name, folder))
        path = os.path.join(folder, typed + '.' + ext)
        if os.path.dirname(os.path.realpath(path)) != os.path.realpath(folder):
            raise ValueError('"%s" would be written outside %s.'
                             % (name, folder))
        return path
