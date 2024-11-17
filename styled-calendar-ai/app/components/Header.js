import './Header.css';

const Header = () => {
  return (
    <header>
      <div className="header-container">
        <div className='logo-title-container'>
          <img src="/calendarAILogo.png" alt="logo" className="logo" width={50} height={50}/>
          <h1 className="page-title">AI Meeting Scheduler</h1>
        </div>
        <button className="login-btn">Login</button>
      </div>
    </header>
  );
}

export default Header;