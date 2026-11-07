import { foundFacts, rebindOffers, scanButton, scanNote, type HealthState } from "../health/health";
import { useRefusal, useSender } from "../wire/store";
import { Badge } from "../design/Badge";
import { Button } from "../design/Button";

/** Find the WLED boards on the network, and point a lost room board at one
 * of them: the MAC match is the evidence, two taps guard the room file. */
export function FindBoards({ health }: { health: HealthState }) {
  const sender = useSender();
  const refusal = useRefusal("rebind");
  const { scan, boards } = health;
  return (
    <div className="find-boards">
      <div className="row">
        <Button
          variant="primary"
          busy={!!scan?.running}
          title="ask every address on this network for WLED's /json/info"
          onPress={() => sender.send({ type: "scan" })}
        >
          {scanButton(scan)}
        </Button>
        <span className="note">{scanNote(scan)}</span>
      </div>
      {scan && !scan.running && (
        <ul className="found">
          {scan.found.map((f) => (
            <li key={f.address}>
              <strong className="t-code">{f.address}</strong>
              <span>{f.name ?? "?"}</span>
              {f.board && <Badge>this is {f.board}</Badge>}
              {f.at && <Badge>{f.at} streams here</Badge>}
              {rebindOffers(f, boards).map((board) => (
                <Button
                  key={board}
                  title={`write ${f.address} as board ${board}'s address in the room file`}
                  confirm={`again to use for ${board}`}
                  disarmOn={refusal ?? scan}
                  onPress={() => sender.send({ type: "rebind", board, address: f.address })}
                >
                  use for {board}
                </Button>
              ))}
              <span className="sub note t-value">{foundFacts(f)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
