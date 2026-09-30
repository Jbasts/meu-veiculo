import { BrowserRouter, Route, Routes } from "react-router";

import { RotaProtegida, RotaSoParaVisitante } from "./components/Rotas";
import { AuthProvider } from "./contexts/AuthContext";
import CadastroPage from "./pages/CadastroPage";
import ContaPage from "./pages/ContaPage";
import EsqueciSenhaPage from "./pages/EsqueciSenhaPage";
import InicioPage from "./pages/InicioPage";
import LoginPage from "./pages/LoginPage";
import NaoEncontradaPage from "./pages/NaoEncontradaPage";
import RedefinirSenhaPage from "./pages/RedefinirSenhaPage";
import SituacaoSistemaPage from "./pages/SituacaoSistemaPage";

/** Endereços do app. Separado do App para os testes usarem um roteador em memória. */
export function RotasDoApp() {
  return (
    <Routes>
      <Route path="/" element={<RotaProtegida><InicioPage /></RotaProtegida>} />
      <Route path="/conta" element={<RotaProtegida><ContaPage /></RotaProtegida>} />
      <Route path="/entrar" element={<RotaSoParaVisitante><LoginPage /></RotaSoParaVisitante>} />
      <Route path="/criar-conta" element={<RotaSoParaVisitante><CadastroPage /></RotaSoParaVisitante>} />
      <Route path="/esqueci-senha" element={<EsqueciSenhaPage />} />
      <Route path="/redefinir-senha" element={<RedefinirSenhaPage />} />
      <Route path="/situacao" element={<SituacaoSistemaPage />} />
      <Route path="*" element={<NaoEncontradaPage />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <RotasDoApp />
      </AuthProvider>
    </BrowserRouter>
  );
}
