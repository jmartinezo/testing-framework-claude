import { Page, Locator } from "@playwright/test";

/**
 * Clase base para todos los Page Objects.
 * Centraliza lógica común: navegación, esperas, utilidades.
 *
 * Todas las páginas del proyecto extienden esta clase.
 */
export abstract class BasePage {
  protected readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  // ---------------------------------------------------------------------------
  // Navegación
  // ---------------------------------------------------------------------------

  /**
   * Navega a la URL de la página.
   * Cada subclase define su propia ruta en `path`.
   */
  async navigate(): Promise<void> {
    await this.page.goto(this.path);
    await this.waitForLoad();
  }

  /**
   * Ruta relativa de la página — sobreescribir en cada subclase.
   */
  protected get path(): string {
    return "/";
  }

  // ---------------------------------------------------------------------------
  // Esperas
  // ---------------------------------------------------------------------------

  /**
   * Espera a que la página esté completamente cargada.
   * Sobreescribir si la página tiene indicadores de carga específicos.
   */
  async waitForLoad(): Promise<void> {
    await this.page.waitForLoadState("networkidle");
  }

  // ---------------------------------------------------------------------------
  // Utilidades
  // ---------------------------------------------------------------------------

  /**
   * Devuelve el título de la página actual.
   */
  async getTitle(): Promise<string> {
    return this.page.title();
  }

  /**
   * Devuelve la URL actual.
   */
  getCurrentUrl(): string {
    return this.page.url();
  }

  /**
   * Hace scroll hasta un elemento.
   */
  async scrollTo(locator: Locator): Promise<void> {
    await locator.scrollIntoViewIfNeeded();
  }

  /**
   * Espera a que un elemento sea visible.
   */
  async waitForVisible(locator: Locator): Promise<void> {
    await locator.waitFor({ state: "visible" });
  }

  /**
   * Toma un screenshot con nombre descriptivo.
   */
  async screenshot(name: string): Promise<void> {
    await this.page.screenshot({
      path: `reports/screenshots/${name}.png`,
      fullPage: true,
    });
  }
}
