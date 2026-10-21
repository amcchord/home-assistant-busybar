import assert from "node:assert/strict";
import vm from "node:vm";

const source = await Deno.readTextFile(
  new URL("../custom_components/busybar_playground/www/busybar-playground-card.js", import.meta.url),
);

Deno.test("Playground card coexists with busybar-card and calls only Playground services", async () => {
  const elements = new Map([["busybar-card", class {}]]);
  const context = vm.createContext({
    HTMLElement: class {
      attachShadow() {
        this.shadowRoot = { querySelector: () => null };
      }
    },
    customElements: {
      define(name, element) {
        assert.equal(elements.has(name), false, `Duplicate element: ${name}`);
        elements.set(name, element);
      },
    },
    document: { createElement: (name) => ({ localName: name }) },
    window: { customCards: [{ type: "busybar-card" }] },
  });
  vm.runInContext(source, context);
  const Card = elements.get("busybar-playground-card");
  assert.ok(Card);
  assert.ok(elements.has("busybar-playground-card-editor"));
  assert.equal(Card.getConfigElement().localName, "busybar-playground-card-editor");
  assert.equal(context.window.customCards[1].type, "busybar-playground-card");

  const card = new Card();
  card._config = { device_id: "playground-device" };
  let call;
  card._hass = { callService: (...args) => { call = args; } };
  await card._call("show_message", { message: "HELLO" });
  assert.deepEqual(JSON.parse(JSON.stringify(call)), [
    "busybar_playground", "show_message",
    { device_id: ["playground-device"], message: "HELLO" },
  ]);
});
