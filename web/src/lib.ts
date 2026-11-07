/**
 * The control page's parts that other pages use: the hosted studio imports
 * its controls from here and its look from `@pewpew/page/styles.css`, so the
 * two pages share one design system.
 */

export { Badge } from "./ui/common/Badge";
export { Button, IconButton, ToggleButton } from "./ui/common/Button";
export { Details } from "./ui/common/Details";
export { DisclosureButton, DisclosureNote, useDisclosure } from "./ui/common/Disclosure";
export { ErrorBoundary } from "./ui/common/ErrorBoundary";
export { Icon, type IconName } from "./ui/common/Icon";
export { Panel, PanelHead } from "./ui/common/Panel";
export { Select, type SelectItem } from "./ui/common/Select";
export { spaced } from "./ui/common/spaced";
export { Switch } from "./ui/common/Switch";
export { Tile } from "./ui/common/Tile";
