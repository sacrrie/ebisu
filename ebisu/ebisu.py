def recallProbabilityMean(alpha, beta, t, tnow):
  # `Integrate[p^((a - t)/t) * (1 - p^(1/t))^(b - 1) * (p)/t/(Gamma[a]*Gamma[b]/Gamma[a+b]), {p, 0, 1}]`
  from scipy.special import gammaln
  from math import exp
  dt = tnow / t
  return exp(
      gammaln(alpha + dt) - gammaln(alpha + beta + dt) - (
          gammaln(alpha) - gammaln(alpha + beta)))


def recallProbabilityVar(alpha, beta, t, tnow):
  from scipy.special import gamma
  # `Assuming[a>0 && b>0 && t>0, {Integrate[p^((a - t)/t) * (1 - p^(1/t))^(b - 1) * (p-m)^2/t/(Gamma[a]*Gamma[b]/Gamma[a+b]), {p, 0, 1}]}]``
  # And then plug in mean for `m` & simplify to get:
  dt = tnow / t
  same0 = gamma(alpha) / gamma(alpha + beta)
  same1 = gamma(alpha + dt) / gamma(alpha + beta + dt)
  same2 = gamma(alpha + 2 * dt) / gamma(alpha + beta + 2 * dt)
  md = same1 / same0
  md2 = same2 / same0
  return md2 - md**2


def posteriorAnalytic(alpha, beta, t, result, tnow):
  from scipy.special import gammaln, gamma
  from math import exp
  dt = tnow / t
  if result == 1:
    # marginal: `Integrate[p^((a - t)/t)*(1 - p^(1/t))^(b - 1)*p, {p,0,1}]`
    # mean: `Integrate[p^((a - t)/t)*(1 - p^(1/t))^(b - 1)*p*p, {p,0,1}]`
    # variance: `Integrate[p^((a - t)/t)*(1 - p^(1/t))^(b - 1)*p*(p - m)^2, {p,0,1}]`
    # Simplify all three to get the following:
    same = gammaln(alpha + beta + dt) - gammaln(alpha + dt)
    mu = exp(gammaln(alpha + 2 * dt) - gammaln(alpha + beta + 2 * dt) + same)
    var = exp(same + gammaln(alpha + 3 * dt) -
              gammaln(alpha + beta + 3 * dt)) - mu**2
  else:
    # Mathematica code is same as above, but replace one `p` with `(1-p)`
    # marginal: `Integrate[p^((a - t)/t)*(1 - p^(1/t))^(b - 1)*(1-p), {p,0,1}]`
    # mean: `Integrate[p^((a - t)/t)*(1 - p^(1/t))^(b - 1)*(1-p)*p, {p,0,1}]`
    # var: `Integrate[p^((a - t)/t)*(1 - p^(1/t))^(b - 1)*(1-p)*(p - m)^2, {p,0,1}]`
    # Then simplify and combine
    same0 = gamma(alpha) / gamma(alpha + beta)
    same1 = gamma(alpha + dt) / gamma(alpha + beta + dt)
    same2 = gamma(alpha + 2 * dt) / gamma(alpha + beta + 2 * dt)
    same3 = gamma(alpha + 3 * dt) / gamma(alpha + beta + 3 * dt)
    mu = (same1 - same2) / (same0 - same1)
    var = (same3 * (same1 - same0) + same2 *
           (same0 + same1 - same2) - same1**2) / (same1 - same0)**2
  newAlpha, newBeta = meanVarToBeta(mu, var)
  return newAlpha, newBeta, tnow


def meanVarToBeta(mean, var):
  # [betaFit] https://en.wikipedia.org/w/index.php?title=Beta_distribution&oldid=774237683#Two_unknown_parameters
  tmp = mean * (1 - mean) / var - 1
  alpha = mean * tmp
  beta = (1 - mean) * tmp
  return alpha, beta


def priorToHalflife(alpha, beta, t, percentile=0.5, maxt=100, mint=1e-3):
  from math import sqrt
  from scipy.optimize import brentq
  h = brentq(
      lambda now: recallProbabilityMean(alpha, beta, t, now) - percentile, mint,
      maxt)
  # `h` is the expected half-life, i.e., the time at which recall probability drops to 0.5.
  # To get the variance about this half-life, we have to convert probability variance (around 0.5) to a time variance. This is a really dumb way to do that:
  # - `v` is the probability variance around 0.5, so `sqrt(v)` is the standard deviation
  # - find the times for which `0.5 +/- sqrt(v)`. This is a kind of one-sigma confidence interval in time
  # - convert these times to a 'time variance' by taking their mean-absolute-distance to `h` and squaring that.
  # Open to suggestions for improving this. The second 'variance' number should not be taken seriously, but it can be used for notional plotting.
  v = recallProbabilityVar(alpha, beta, t, h)
  h2 = brentq(
      lambda now: recallProbabilityMean(alpha, beta, t, now) - (percentile - sqrt(v)),
      mint, maxt)
  h3 = brentq(
      lambda now: recallProbabilityMean(alpha, beta, t, now) - (percentile + sqrt(v)),
      mint, maxt)

  return h, ((abs(h2 - h) + abs(h3 - h)) / 2)**2
