export const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json' },
  });

export const isAdmin = (request, env) =>
  !!env.ADMIN_TOKEN && request.headers.get('x-admin-token') === env.ADMIN_TOKEN;

const validBox = (b) =>
  b && ['x', 'y', 'w', 'h'].every((k) => typeof b[k] === 'number' && b[k] >= 0 && b[k] <= 1) &&
  b.w > 0.05 && b.h > 0.05;

export const boxesOk = (...boxes) => boxes.every(validBox);

// Libera videos reclamados hace más de 30 min (anotador se fue / cerró la pestaña).
export const releaseStale = (env) =>
  env.DB.prepare(
    `UPDATE videos SET status='pending', claimed_by=NULL, claimed_at=NULL
     WHERE status='claimed' AND claimed_at < datetime('now','-30 minutes')`
  ).run();

