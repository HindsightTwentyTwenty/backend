import React, { Component } from 'react';
import NavBar from './NavBar.js';

// example class based component (smart component)
class LandingPage extends Component {
  constructor(props) {
    super(props);
    // init component state here
    this.state = {};
  }

  render() {
    return (
      <div>
      <NavBar/>
      <div className="row" id="top-nav-bar">
        <div className="col-md-4" id="nav-bar-img-col">
          <img id="nav-bar-img" src="static/img/logo-light.png"/>
        </div>
        <div className="col-md-4">
          <div className="wrapper">
            <button className="btn btn-primary btn-lg"
                onclick="chrome.webstore.install()"
                role="button">
                  <i className="fa fa-plus"></i> Add to Chrome
            </button>
          </div>
        </div>

        <div className="col-md-4">
        </div>
      </div>
      <div className="jumbotron">
        <div className="container">
          <img src="static/img/logo-light.png"/>
          <h1>hindsite</h1>
          <p>history that’s finally 20/20</p>
          <div className="wrapper">
            <button className="btn btn-primary btn-lg"
                onclick="chrome.webstore.install()"
                role="button">
                  <i className="fa fa-plus"></i> Add to Chrome
            </button>
          </div>
        </div>
      </div>

      <div className="container">
        <div className="row">
          <div className="col-md-4">
            <h2>Lookback</h2>
            <p>This feature allows you to see your history in an intuitive timeline view. It shows you when pages were opened, closed, active, where they overlap and how you moved from one page to another.</p>
          </div>
          <div className="col-md-4">
            <h2>Categories</h2>
            <p>By using hindsites categorization tool, you are able to easily tag pages to go back to later. When you are ready, you can go to your categories page to see all of the pages you have categorized.</p>
         </div>
          <div className="col-md-4">
            <h2>Search</h2>
            <p>Unlike Chrome History, hindsite searches pages in your history by page content as well as by title. This means that hindsite will find your search terms anywhere they are mentioned in the pages you visited.</p>
          </div>
        </div>
      </div>
    </div>
    );
  }
}

// function based "dumb" component with no state
// const Welcome = () => {
//   return (
//
//   );
// };


export default LandingPage;
